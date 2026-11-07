# Plugin VST3 + Standalone (incluído pelo CMakeLists.txt)
juce_add_plugin(Violino
    PRODUCT_NAME "Violino"
    COMPANY_NAME "Violino Project"
    BUNDLE_ID "org.violino.plugin"
    PLUGIN_MANUFACTURER_CODE Vlno
    PLUGIN_CODE Vln1
    FORMATS VST3 Standalone
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    NEEDS_WEBVIEW2 TRUE
    VST3_CATEGORIES Instrument Synth
    COPY_PLUGIN_AFTER_BUILD FALSE)

target_sources(Violino PRIVATE
    source/PluginProcessor.cpp
    source/PluginEditor.cpp
    source/PreviewSampler.cpp
    source/EngineService.cpp)
target_include_directories(Violino PRIVATE source)

juce_add_binary_data(ViolinoUI SOURCES ui/index.html ui/violin.webp)

target_compile_definitions(Violino PUBLIC
    JUCE_WEB_BROWSER=1
    JUCE_USE_WIN_WEBVIEW2_WITH_STATIC_LINKING=1
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0
    JUCE_DISPLAY_SPLASH_SCREEN=0
    NOMINMAX)
target_compile_options(Violino PRIVATE /utf-8)

target_link_libraries(Violino
    PRIVATE
        ViolinoUI
        violino_engine
        juce::juce_audio_utils
        juce::juce_audio_formats
        juce::juce_gui_extra
        juce::juce_dsp
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)

# DLLs do ONNX Runtime/DirectML ao lado do binário de cada formato
copy_runtime_dlls(Violino_Standalone $<TARGET_FILE_DIR:Violino_Standalone>)
copy_runtime_dlls(Violino_VST3 $<TARGET_FILE_DIR:Violino_VST3>)
