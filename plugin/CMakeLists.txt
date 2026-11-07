cmake_minimum_required(VERSION 3.22)
project(Violino VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

set(DEPS ${CMAKE_CURRENT_SOURCE_DIR}/../deps)
set(JUCE_WEBVIEW2_PACKAGE_LOCATION ${DEPS}/nuget)
add_subdirectory(${DEPS}/JUCE ${CMAKE_BINARY_DIR}/JUCE)

# ---- ONNX Runtime (DirectML): DLLs carregadas pelo caminho completo em tempo de execução
set(ORT_DIR ${DEPS}/Microsoft.ML.OnnxRuntime.DirectML)
set(DML_DIR ${DEPS}/Microsoft.AI.DirectML)
set(RUNTIME_DLLS
    ${ORT_DIR}/runtimes/win-x64/native/onnxruntime.dll
    ${ORT_DIR}/runtimes/win-x64/native/onnxruntime_providers_shared.dll
    ${DML_DIR}/bin/x64-win/DirectML.dll)

# ---- motor (sem JUCE): articulador, VIOLET em ONNX, escolha de takes, mixer
add_library(violino_engine STATIC
    engine/Articulator.cpp
    engine/VioletRenderer.cpp
    engine/Performer.cpp
    engine/MixFx.cpp)
target_include_directories(violino_engine PUBLIC engine PRIVATE ${ORT_DIR}/build/native/include)
target_compile_definitions(violino_engine PRIVATE ORT_API_MANUAL_INIT NOMINMAX)
target_link_libraries(violino_engine PUBLIC ${ORT_DIR}/runtimes/win-x64/native/onnxruntime.lib dxgi delayimp)
target_link_options(violino_engine INTERFACE /DELAYLOAD:onnxruntime.dll)
target_compile_options(violino_engine PRIVATE /W3 /utf-8)

function(copy_runtime_dlls target dest)
    foreach(dll ${RUNTIME_DLLS})
        add_custom_command(TARGET ${target} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different ${dll} ${dest})
    endforeach()
endfunction()

# ---- ferramenta de linha de comando (testes do motor)
juce_add_console_app(violino_cli PRODUCT_NAME "violino_cli")
target_sources(violino_cli PRIVATE cli/Main.cpp)
target_compile_definitions(violino_cli PRIVATE JUCE_USE_CURL=0 JUCE_WEB_BROWSER=0)
target_compile_options(violino_cli PRIVATE /utf-8)
target_link_libraries(violino_cli PRIVATE violino_engine juce::juce_audio_formats juce::juce_audio_basics
                      juce::juce_recommended_config_flags juce::juce_recommended_warning_flags)
copy_runtime_dlls(violino_cli $<TARGET_FILE_DIR:violino_cli>)

if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/source/PluginProcessor.cpp)
    include(plugin.cmake)
endif()
