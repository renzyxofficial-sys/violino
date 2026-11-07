#include "PluginEditor.h"

#include <BinaryData.h>

namespace
{
juce::WebBrowserComponent::Options webOptions (ViolinoProcessor& proc,
                                               std::function<std::optional<juce::WebBrowserComponent::Resource> (const juce::String&)> provider)
{
    using O = juce::WebBrowserComponent::Options;
    return O {}
        .withBackend (O::Backend::webview2)
        .withWinWebView2Options (O::WinWebView2 {}
                                     .withUserDataFolder (Paths::dataDir().getChildFile ("webview"))
                                     .withBackgroundColour (juce::Colour (0xff1e1e1f)))
        .withNativeIntegrationEnabled()
        .withResourceProvider (std::move (provider))
        .withEventListener ("cmd", [&proc] (const juce::var& v) { proc.handleUiCommand (v); });
}
} // namespace

ViolinoEditor::ViolinoEditor (ViolinoProcessor& p)
    : juce::AudioProcessorEditor (p), proc (p),
      web (webOptions (p, [this] (const juce::String& url) { return resource (url); }))
{
    addAndMakeVisible (web);
    scaling = true;  // limites e tamanho iniciais não contam como escolha do usuário
    setResizable (true, true);
    getConstrainer()->setFixedAspectRatio (1280.0 / 940.0);
    setResizeLimits (840, 617, 2240, 1644);  // 75 % a 200 %
    applyScale();
    proc.onExportRequested = [this] { chooseExportFile(); };
    proc.onImportRequested = [this] {
        chooser = std::make_unique<juce::FileChooser> ("Import MIDI", juce::File::getSpecialLocation (juce::File::userMusicDirectory), "*.mid;*.midi");
        chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles, [this] (const juce::FileChooser& fc) {
            auto f = fc.getResult();
            if (f == juce::File {}) return;
            juce::var c (new juce::DynamicObject());
            c.getDynamicObject()->setProperty ("cmd", "importMidi");
            c.getDynamicObject()->setProperty ("path", f.getFullPathName());
            proc.handleUiCommand (c);  // passa pelo desfazer como qualquer edição
        });
    };
    proc.onScaleChanged = [this] { applyScale(); };
    proc.onDragRequested = [this] (const juce::File& f) {
        // o botão do mouse ainda está pressionado na alça "Drag": começa o arrasto do WAV
        juce::DragAndDropContainer::performExternalDragDropOfFiles ({ f.getFullPathName() }, false, this);
    };
    web.goToURL (juce::WebBrowserComponent::getResourceProviderRoot());
    startTimerHz (15);
}

ViolinoEditor::~ViolinoEditor()
{
    proc.onExportRequested = nullptr;
    proc.onImportRequested = nullptr;
    proc.onScaleChanged = nullptr;
    proc.onDragRequested = nullptr;
}

void ViolinoEditor::applyScale()
{
    if (! bool (Settings::get ("scale125", false)))
        Settings::set ("scale125", true), Settings::set ("uiScale", 1.25);
    const double s = juce::jlimit (0.75, 2.0, double (Settings::get ("uiScale", 1.25)));
    scaling = true;
    setSize (juce::roundToInt (kBaseW * s), juce::roundToInt (kBaseH * s));
    scaling = false;
}

void ViolinoEditor::resized()
{
    web.setBounds (getLocalBounds());
    if (! scaling && getWidth() > 0)  // redimensionado pela borda: guarda a escala
        Settings::set ("uiScale", juce::jlimit (0.75, 2.0, getWidth() / double (kBaseW)));
}

void ViolinoEditor::timerCallback()
{
    if (proc.wrapperType == juce::AudioProcessor::wrapperType_Standalone && focusTicks < 30 && ++focusTicks % 10 == 0 && isShowing() && ! web.hasKeyboardFocus (true))
        web.grabKeyboardFocus();  // a página recebe o teclado logo ao abrir (Espaço = play)
    const double t0 = juce::Time::getMillisecondCounterHiRes();
    auto st = proc.buildUiState();
    web.emitEventIfBrowserIsVisible ("state", st);
    if (const double d = juce::Time::getMillisecondCounterHiRes() - t0; d > 40) appLog ("slow ui state: " + juce::String (juce::roundToInt (d)) + " ms");
}

std::optional<juce::WebBrowserComponent::Resource> ViolinoEditor::resource (const juce::String& url)
{
    auto name = url == "/" ? juce::String ("index.html") : url.fromLastOccurrenceOf ("/", false, false);
    for (int i = 0; i < BinaryData::namedResourceListSize; ++i)
    {
        if (name != BinaryData::originalFilenames[i]) continue;
        int size = 0;
        auto* data = BinaryData::getNamedResource (BinaryData::namedResourceList[i], size);
        std::vector<std::byte> bytes ((const std::byte*) data, (const std::byte*) data + size);
        auto mime = name.endsWith (".html") ? "text/html" : name.endsWith (".webp") ? "image/webp" : name.endsWith (".js") ? "text/javascript" : "application/octet-stream";
        return juce::WebBrowserComponent::Resource { std::move (bytes), mime };
    }
    return std::nullopt;
}

void ViolinoEditor::chooseExportFile()
{
    chooser = std::make_unique<juce::FileChooser> ("Export WAV",
                                                   juce::File::getSpecialLocation (juce::File::userMusicDirectory).getChildFile ("Violin.wav"), "*.wav");
    chooser->launchAsync (juce::FileBrowserComponent::saveMode | juce::FileBrowserComponent::canSelectFiles | juce::FileBrowserComponent::warnAboutOverwriting,
                          [this] (const juce::FileChooser& fc) {
                              auto f = fc.getResult();
                              if (f == juce::File {}) return;
                              juce::String err;
                              if (! proc.exportWav (f.withFileExtension ("wav"), err))
                                  juce::AlertWindow::showMessageBoxAsync (juce::MessageBoxIconType::WarningIcon, "Export WAV", err);
                          });
}
