import soundfile as sf, glob, os, collections
root = r"C:\Users\TheoH\violino\deps\VSCO-2-CE\Strings\Solo Violin"
for d in sorted(os.listdir(root)):
    fs = sorted(glob.glob(os.path.join(root, d, "*.wav")))
    infos = [sf.info(f) for f in fs]
    durs = [i.duration for i in infos]
    print(d, len(fs), "sr", set(i.samplerate for i in infos), "ch", set(i.channels for i in infos), set(i.subtype for i in infos),
          "dur %.1f-%.1f s" % (min(durs), max(durs)), [os.path.basename(f) for f in fs[:3]])
