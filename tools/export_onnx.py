"""Exporta o VIOLET para ONNX (DiT de um passo + decodificador DACVAE) e grava uma janela de referência.

Roda no WSL, conda violet, copiado para ~/VIOLET/src/ (mesmo esquema do bench_violet.py):
    REF_MIDI=/mnt/c/.../teste.mid OUT_DIR=/mnt/c/Users/TheoH/violino/onnx python src/export_onnx.py

Saídas em OUT_DIR:
  violet_dit.onnx     v = dit(x, t, midi_roll, tech_roll, tech_keep, cc_tokens, cc_keep)
  dacvae_decode.onnx  wav = decode(latents)
  reference.npz       entradas e saídas do PyTorch para uma janela de 10 s (para validar o ONNX)

Com a configuração de inferência do VIOLET (cond_scale=None, w_tech=1, w_cc=0) a guidance
composicional vira pred_m + 1·(pred_mt − pred_m) = pred_mt: basta UMA chamada da rede por avaliação
(técnica ligada, CC desligado), em vez das duas que o PyTorch faz.
"""
import os
import pickle
from pathlib import Path
import sys

sys.path.insert(0, os.getcwd())

import hydra  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from torch import nn  # noqa: E402

from note_seq import midi_io  # noqa: E402
from src.data.components.midi_processor import load_technique_map  # noqa: E402
from src.inference.long_audio import prepare_eval_aligned_windows, _batch_window_dicts  # noqa: E402
from src.inference.render_utils import make_seeded_noise  # noqa: E402
from src.models.backbones import attention_utils as au  # noqa: E402
from src.models.backbones.dit import modulate  # noqa: E402
from src.models.components.dacvae_wrapper import FTDACVAE  # noqa: E402


# O RoPE do VIOLET usa números complexos (torch.polar / view_as_complex), que o ONNX não tem.
# Versão equivalente em reais: guarda só os ângulos e gira os pares (par, ímpar) com cos/sen.
def real_freqs(dim, end, theta=10000.0, device=torch.device("cpu")):
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float().to(device) / dim))
    return torch.outer(torch.arange(end).to(device).float(), freqs)


def real_rotary(xq, xk, freqs_cis, rotary_dim=None):
    head_dim = xq.shape[-1]
    rotary_dim = min(head_dim if rotary_dim is None else rotary_dim, head_dim)
    rotary_dim -= rotary_dim % 2
    if rotary_dim <= 0:
        return xq, xk
    ang = freqs_cis[..., : rotary_dim // 2]
    cos, sin = ang.cos()[None, :, None, :], ang.sin()[None, :, None, :]

    def rot(x, n):
        xr = x[..., :rotary_dim].float().reshape(*x.shape[:-1], -1, 2)
        a, b = xr[..., 0], xr[..., 1]
        c, s = cos[:, :n], sin[:, :n]
        out = torch.stack((a * c - b * s, a * s + b * c), dim=-1).flatten(3)
        return torch.cat((out.type_as(x), x[..., rotary_dim:]), dim=-1)

    return rot(xq, xq.shape[1]), rot(xk, xk.shape[1])


def matmul_attention(self, x, return_attn_weights=False):
    """Attention.forward do VIOLET com matmul no lugar de einsum("... n d, ... m d").

    O DirectML não tem Einsum com reticências: cai na CPU com cópias GPU<->CPU (~90% do tempo).
    """
    q = self.to_q(x)
    k, v = self.to_kv(x).chunk(2, dim=-1)
    if self.use_rope:
        q, k = au.rearrange_many((q, k), "b n (h d) -> b n h d", h=self.heads)
        q, k = au.apply_rotary_emb(q, k, freqs_cis=self._get_freqs_cis(k.shape[1], k.device),
                                   rotary_dim=self._rotary_dim_from_frac(self.self_rope_rotary_frac))
        q, k = au.rearrange_many((q, k), "b n h d -> b n (h d)")
    q, k, v = au.rearrange_many((q, k, v), "b n (h d) -> b h n d", h=self.heads)
    if self.use_qk_l2norm:
        q, k = map(au.l2norm, (q, k))
        q = q * self.q_scale
        k = k * self.k_scale
    sim = torch.matmul(q, k.transpose(-1, -2)) * self.scale
    attn = sim.softmax(dim=-1, dtype=torch.float32).to(sim.dtype)
    out = au.rearrange(torch.matmul(attn, v), "b h n d -> b n (h d)").contiguous()
    return self.to_out(out).contiguous()


def use_real_rope(net):
    au.compute_freqs_cis = real_freqs
    au.apply_rotary_emb = real_rotary
    au.Attention.forward = matmul_attention
    for m in net.modules():
        if isinstance(m, au.Attention):
            m.freqs_cis_dict = {}
            m._rope_freqs_cis = None


class DiTStep(nn.Module):
    """Uma avaliação da rede com as máscaras de presença como entradas (0 = condição nula)."""

    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, x, t, midi_roll, tech_roll, tech_keep, cc_tokens, cc_keep):
        return self.net(x, t, cc_tokens=cc_tokens, midi_roll=midi_roll, tech_roll=tech_roll,
                        cc_keep_mask=cc_keep, tech_roll_keep_mask=tech_keep,
                        cond_drop_prob=0.0, midi_cond_drop_prob=0.0,
                        tech_cond_drop_prob=0.0, cc_cond_drop_prob=0.0)


class DiTCond(nn.Module):
    """Tudo que depende só do MIDI: roda uma vez por janela, fora do laço do amostrador.

    Devolve a modulação local já somada (CC + notas + técnica) de cada bloco e da camada final;
    no DiT essas projeções não dependem de x nem de t, então pré-calcular corta ~metade da conta.
    """

    def __init__(self, net, frames=250):
        super().__init__()
        self.net, self.frames = net, frames

    def forward(self, midi_roll, tech_roll, tech_keep, cc_tokens, cc_keep):
        net, T = self.net, self.frames
        midi_feat = net.midi_harmonic_extractor(midi_roll, target_len=T)
        midi = net.midi_roll_frame_embedder(midi_feat.transpose(1, 2), target_len=T, cc_keep=None)
        tech_feat = net.tech_roll_extractor(tech_roll, target_len=T)
        tech = net.tech_roll_frame_embedder(tech_feat.transpose(1, 2), target_len=T, cc_keep=tech_keep)
        cc = net.cc_frame_embedder(cc_tokens, target_len=T, cc_keep=cc_keep)

        def local(m):
            return m.cc_modulation(cc) + m.midi_roll_modulation(midi) + m.tech_roll_modulation(tech)

        return torch.stack([local(b) for b in net.blocks], 0), local(net.final_layer)


class DiTCore(nn.Module):
    """Uma avaliação da rede dentro do laço: v = core(x, t, modulações pré-calculadas)."""

    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, x, t, block_mod, final_mod):
        net = self.net
        x = net.x_embedder(x.transpose(1, 2))
        c = net.t_embedder(t.float()).to(x.dtype)  # embedding de tempo sempre em fp32
        for i, b in enumerate(net.blocks):
            mod = b.adaLN_modulation(c).unsqueeze(1) + block_mod[i]
            shift_msa, scale_msa, gate_msa, shift_mlp, scale_mlp, gate_mlp = mod.chunk(6, dim=2)
            x = x + gate_msa * b.self_attn(modulate(b.norm1(x), shift_msa, scale_msa))
            x = x + gate_mlp * b.mlp(modulate(b.norm2(x), shift_mlp, scale_mlp))
        fl = net.final_layer
        shift, scale = (fl.adaLN_modulation(c).unsqueeze(1) + final_mod).chunk(2, dim=2)
        return fl.linear(modulate(fl.norm_final(x), shift, scale)).transpose(1, 2)


class Decode(nn.Module):
    def __init__(self, codec):
        super().__init__()
        self.codec = codec

    def forward(self, z):
        return self.codec.decode(z)


@hydra.main(version_base="1.3", config_path="../configs", config_name="eval.yaml")
def main(cfg):
    out_dir = os.environ.get("OUT_DIR", "onnx_out")
    ref_midi = os.environ["REF_MIDI"]
    os.makedirs(out_dir, exist_ok=True)
    root = os.environ.get("PROJECT_ROOT", os.getcwd())

    model = hydra.utils.instantiate(cfg.model)
    with open(cfg.model.ema_ckpt_path, "rb") as f:
        ema_net = pickle.load(f)
    state = ema_net.state_dict()
    model._migrate_legacy_dit_state_dict(state, model.net.state_dict())
    model.net.load_state_dict(state, strict=True)
    codec = FTDACVAE.load_with_finetuned_weights(
        base_ckpt=cfg.encoder.base_ckpt, finetuned_ckpt=cfg.encoder.finetuned_ckpt,
        use_finetuned=cfg.encoder.use_finetuned, posterior_mode=cfg.encoder.posterior_mode)
    model.codec_model = codec
    dev = torch.device("cuda")
    model.to(dev).eval()
    codec.to(dev).eval()

    # ---- janela de referência com as funções do próprio VIOLET ----
    tech_map = load_technique_map(Path(root) / "configs/ks_config.yaml")
    seq = midi_io.midi_file_to_note_sequence(ref_midi)
    windows, *_ = prepare_eval_aligned_windows(
        midi_path=ref_midi, technique_map=tech_map, technique_pitch_keys=set(tech_map),
        sequence=seq, total_duration=10.0, window_seconds=10.0, overlap=0.5,
        frame_rate=float(model.cc_frame_rate), use_midi_roll=True, use_tech_roll=True,
        midi_roll_min_pitch=55, midi_roll_max_pitch=105, num_techniques=13,
        tech_roll_note_duration_seconds=None)
    batch = _batch_window_dicts([windows[0]], device=dev, dtype=torch.float32)
    kw = model._prepare_conditioning_kwargs(batch)
    noise = make_seeded_noise((1, model.latent_dim, model.generated_frame_length), seed=1234,
                              device=dev, dtype=torch.float32)
    with torch.no_grad():
        lat_ref = model.synthesize_from_noise(noise, batch)
        wav_ref = codec.decode(lat_ref.float())
    sigmas = torch.as_tensor(model.noise_scheduler).cpu().numpy()
    tech_keep = kw.get("tech_roll_keep_mask", torch.ones(1, 1, 1, device=dev))
    cc_tokens = kw["cc_tokens"]
    print("shapes:", {k: tuple(v.shape) for k, v in kw.items()}, "sigmas", sigmas.shape)
    np.savez(os.path.join(out_dir, "reference.npz"),
             noise=noise.cpu().numpy(), midi_roll=kw["midi_roll"].cpu().numpy(),
             tech_roll=kw["tech_roll"].cpu().numpy(), tech_keep=tech_keep.cpu().numpy(),
             cc_tokens=cc_tokens.cpu().numpy(), sigmas=sigmas,
             latents=lat_ref.cpu().numpy(), wav=wav_ref.cpu().numpy())

    # ---- exportação ----
    step = DiTStep(model.net).eval()
    x = noise
    t = torch.full((1,), 0.5, device=dev)
    zero_cc = torch.zeros(1, 1, 1, device=dev)
    args = (x, t, kw["midi_roll"], kw["tech_roll"], tech_keep, cc_tokens, zero_cc)
    with torch.no_grad():
        v_check = step(*args)
        use_real_rope(model.net)
        v_real = step(*args)
    print("rope real vs complexo: max |dv| =", float((v_real - v_check).abs().max()),
          "| max |v| =", float(v_check.abs().max()))
    np.savez(os.path.join(out_dir, "dit_check.npz"), t=0.5, v=v_check.cpu().numpy())
    # rede separada: condicionamento (1x por janela) + núcleo (cada avaliação do amostrador)
    for m in list(model.net.blocks) + [model.net.final_layer]:
        assert all(hasattr(m, a) for a in ("cc_modulation", "midi_roll_modulation", "tech_roll_modulation"))
    cond, core = DiTCond(model.net).eval(), DiTCore(model.net).eval()
    cond_args = (kw["midi_roll"], kw["tech_roll"], tech_keep, cc_tokens, zero_cc)
    with torch.no_grad():
        block_mod, final_mod = cond(*cond_args)
        v_split = core(x, t, block_mod, final_mod)
    print("separada vs inteira: max |dv| =", float((v_split - v_real).abs().max()),
          "| block_mod", tuple(block_mod.shape))
    names = ["midi_roll", "tech_roll", "tech_keep", "cc_tokens", "cc_keep"]
    torch.onnx.export(cond, cond_args, os.path.join(out_dir, "violet_cond.onnx"), dynamo=False,
                      input_names=names, output_names=["block_mod", "final_mod"], opset_version=17,
                      do_constant_folding=True)
    # formas fixas (lote 1): com eixos dinâmicos o grafo ganha ~1800 ops de Shape/Gather/Concat
    # que o DirectML executa na CPU, sincronizando a GPU a cada uma
    core_axes = None
    core_names = ["x", "t", "block_mod", "final_mod"]
    torch.onnx.export(core, (x, t, block_mod, final_mod), os.path.join(out_dir, "violet_core.onnx"),
                      dynamo=False, input_names=core_names, output_names=["v"], opset_version=17,
                      dynamic_axes=core_axes)
    # núcleo em meia precisão (metade do tamanho; mais rápido na GPU)
    core16 = DiTCore(model.net.half()).eval()
    model.net.t_embedder.float()
    h = lambda a: a.half()  # noqa: E731
    with torch.no_grad():
        v16 = core16(h(x), h(t), h(block_mod), h(final_mod)).float()
    print("fp16 vs fp32: max |dv| =", float((v16 - v_split).abs().max()))
    torch.onnx.export(core16, (h(x), h(t), h(block_mod), h(final_mod)),
                      os.path.join(out_dir, "violet_core_fp16.onnx"), dynamo=False,
                      input_names=core_names, output_names=["v"], opset_version=17,
                      dynamic_axes=core_axes)
    model.net.float()
    print("dit ok")

    if not os.path.exists(os.path.join(out_dir, "dacvae_decode.onnx")):
        dec = Decode(codec).eval()
        torch.onnx.export(dec, (lat_ref.float(),), os.path.join(out_dir, "dacvae_decode.onnx"),
                          dynamo=False, input_names=["latents"], output_names=["wav"], opset_version=17,
                          dynamic_axes={"latents": {0: "batch"}, "wav": {0: "batch"}})
    print("decode ok")


if __name__ == "__main__":
    main()
