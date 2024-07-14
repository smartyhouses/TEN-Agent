#
#
# Agora Real Time Engagement
# Created by Wei Hu in 2024-05.
# Copyright (c) 2024 Agora IO. All rights reserved.
#
#
from rte_runtime_python import (
    Addon,
    Extension,
    register_addon_as_extension,
    Rte,
    Cmd,
    PcmFrame,
    RTE_PCM_FRAME_DATA_FMT,
    Data,
    StatusCode,
    CmdResult,
    MetadataInfo,
    RTE_PIXEL_FMT,
)
from typing import List, Any
import dashscope
from dashscope.audio.tts_v2 import ResultCallback, SpeechSynthesizer, AudioFormat
from .log import logger

class CosyTTSCallback(ResultCallback):
    _player = None
    _stream = None

    def __init__(self, rte: Rte, sample_rate: int):
        super().__init__()
        self.rte = rte
        self.sample_rate = sample_rate
        self.frame_size = int(self.sample_rate * 1 * 2 / 100)

    def on_open(self):
        print("websocket is open.")

    def on_complete(self):
        print("speech synthesis task complete successfully.")

    def on_error(self, message: str):
        print(f"speech synthesis task failed, {message}")

    def on_close(self):
        print("websocket is closed.")

    def on_event(self, message):
        print(f"recv speech synthsis message {message}")

    def get_frame(self, data: bytes) -> PcmFrame:
        f = PcmFrame.create("pcm_frame")
        f.set_sample_rate(self.sample_rate)
        f.set_bytes_per_sample(2)
        f.set_number_of_channels(1)
        # f.set_timestamp = 0
        f.set_data_fmt(RTE_PCM_FRAME_DATA_FMT.RTE_PCM_FRAME_DATA_FMT_INTERLEAVE)
        f.set_samples_per_channel(self.sample_rate // 100)
        f.alloc_buf(len(data))
        buff = f.lock_buf()
        buff[:] = data
        f.unlock_buf(buff)
        return f

    def on_data(self, data: bytes) -> None:
        print("audio result length:", len(data), self.frame_size)
        try:
          chunk = int(len(data) / self.frame_size)
          offset = 0
          for i in range(0, chunk):
              #print("****", i, offset, self.frame_size)
              f = self.get_frame(data[offset:offset + self.frame_size])
              self.rte.send_pcm_frame(f)
              #print("send pcm chunk", i)
              offset += self.frame_size
          
          if offset < len(data):
              #print("-----")
              size = len(data) - offset
              f = self.get_frame(data[offset:offset+size])
              self.rte.send_pcm_frame(f)
              #print("send last pcm chunk")
        except Exception as e:
            print("exception:", e)

class CosyTTSExtension(Extension):
    def __init__(self, name: str):
        super().__init__(name)
        self.api_key = ""
        self.voice = ""
        self.model = ""
        self.sample_rate = 16000
        self.tts = None
        self.callback = None
        
    def on_msg(self, msg: str):
        print("on message", msg)
        self.tts.streaming_call(msg)

    def on_init(
        self, rte: Rte, manifest: MetadataInfo, property: MetadataInfo
    ) -> None:
        print("CosyTTSExtension on_init")
        rte.on_init_done(manifest, property)

    def on_start(self, rte: Rte) -> None:
        print("CosyTTSExtension on_start")
        self.api_key = rte.get_property_string("api_key")
        self.voice = rte.get_property_string("voice")
        self.model = rte.get_property_string("model")
        self.sample_rate = rte.get_property_int("sample_rate")

        dashscope.api_key = self.api_key
        f = AudioFormat.PCM_16000HZ_MONO_16BIT
        if self.sample_rate == 8000:
            f = AudioFormat.PCM_8000HZ_MONO_16BIT  
        elif self.sample_rate == 16000:
            f = AudioFormat.PCM_16000HZ_MONO_16BIT
        elif self.sample_rate == 22050:
          f = AudioFormat.PCM_22050HZ_MONO_16BIT
        elif self.sample_rate == 24000:
          f = AudioFormat.PCM_24000HZ_MONO_16BIT
        elif self.sample_rate == 44100:
          f = AudioFormat.PCM_44100HZ_MONO_16BIT
        elif self.sample_rate == 48000:
          f = AudioFormat.PCM_48000HZ_MONO_16BIT
        else:
          print("unknown sample rate", self.sample_rate)
          exit()

        self.callback = CosyTTSCallback(rte, self.sample_rate)
        self.tts = SpeechSynthesizer(model=self.model, voice=self.voice, format=f, callback=self.callback)
        rte.on_start_done()

    def on_stop(self, rte: Rte) -> None:
        print("CosyTTSExtension on_stop")
        self.tts.streaming_complete()
        rte.on_stop_done()

    def on_deinit(self, rte: Rte) -> None:
        print("CosyTTSExtension on_deinit")
        rte.on_deinit_done()

    def on_data(self, rte: Rte, data: Data) -> None:
        print("CosyTTSExtension on_data")
        inputText = data.get_property_string("text")
        if len(inputText) == 0:
            print("ignore empty text")
            return
        
        print("on data", inputText)
        self.on_msg(inputText)

    def on_cmd(self, rte: Rte, cmd: Cmd) -> None:
        print("CosyTTSExtension on_cmd")
        cmd_json = cmd.to_json()
        print("CosyTTSExtension on_cmd json: " + cmd_json)

        cmd_result = CmdResult.create(StatusCode.OK)
        cmd_result.set_property_string("detail", "success")
        rte.return_result(cmd_result, cmd)

@register_addon_as_extension("cosy_tts")
class CosyTTSExtensionAddon(Addon):
    def on_init(self, rte: Rte, manifest, property) -> None:
        print("CosyTTSExtensionAddon on_init")
        rte.on_init_done(manifest, property)
        return

    def on_create_instance(self, rte: Rte, addon_name: str, context) -> None:
        logger.info("on_create_instance")
        rte.on_create_instance_done(CosyTTSExtension(addon_name), context)

    def on_deinit(self, rte: Rte) -> None:
        print("CosyTTSExtensionAddon on_deinit")
        rte.on_deinit_done()
        return