// Janela do plugin: a interface é HTML (o design Liquid Glass) num WebView2, servida do binário.
// C++ -> JS: evento "state" a 15 Hz. JS -> C++: evento "cmd".
#pragma once

#include "PluginProcessor.h"

#include <juce_gui_extra/juce_gui_extra.h>

class ViolinoEditor : public juce::AudioProcessorEditor, private juce::Timer
{
public:
    explicit ViolinoEditor (ViolinoProcessor&);
    ~ViolinoEditor() override;
    void resized() override;

private:
    void timerCallback() override;
    std::optional<juce::WebBrowserComponent::Resource> resource (const juce::String& url);
    void chooseExportFile();
    void applyScale();
    static constexpr int kBaseW = 1120, kBaseH = 822;  // 100 %
    bool scaling = false;
    int focusTicks = 0;

    ViolinoProcessor& proc;
    juce::WebBrowserComponent web;
    std::unique_ptr<juce::FileChooser> chooser;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ViolinoEditor)
};
