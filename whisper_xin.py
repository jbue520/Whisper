import logging
from pydub import AudioSegment
from datetime import timedelta
import os
import shutil
import whisper
import tempfile
import concurrent.futures
import re
# 配置日志
logging.basicConfig(level=logging.INFO)

def clean_text(text: str) -> str:
    """
    清除文本中的特殊字符和标记。
    """
    cleaned_text = re.sub(r'[♪♫♬♭♮♯\[\]#()*+/:;<=>@\\^_`{|}~「」『』]', '', text)
    cleaned_text = re.sub(r'\(SPEAKING FOREIGN LANGUAGE\)', '', cleaned_text)
    cleaned_text = re.sub(r'\[\w+\]', '', cleaned_text)
    cleaned_text = re.sub(r'私はこの本を読むのが好きです。', '', cleaned_text)  # 添加新的清除规则
    return cleaned_text

def update_srt_file(srt_path, segments, offset):
    try:
        with open(srt_path, 'a', encoding='utf-8') as srt_file:
            for idx, segment in enumerate(segments):
                start_time_segment = int(segment['start'] + offset / 1000)
                end_time_segment = int(segment['end'] + offset / 1000)
                text = segment['text']
                cleaned_text = clean_text(text)  # 调用 clean_text 函数来清理文本
                srt_entry = f"{idx + 1}\n"
                srt_entry += str(timedelta(seconds=start_time_segment)) + ',000'
                srt_entry += " --> "
                srt_entry += str(timedelta(seconds=end_time_segment)) + ',000' + "\n"
                srt_entry += f"{cleaned_text}\n\n"  # 使用清理后的文本
                srt_file.write(srt_entry)
        logging.info("SRT 文件已更新。")
    except Exception as e:
        logging.error(f"更新 SRT 文件时发生错误：{e}")


def transcribe_segment(model, segment_audio, start_time, end_time, temp_dir, gain):
    try:
        temp_audio_path = os.path.join(temp_dir, f"segment_{start_time}_{end_time}.mp3")
        segment_audio.export(temp_audio_path, format="mp3")
        segment_audio = segment_audio.apply_gain(gain)  # 使用参数化的增益值

        logging.info(f"保存临时音频文件：{temp_audio_path}")

        transcribe_result = model.transcribe(audio=temp_audio_path)
        logging.info(f"完成音频段的转录。结果：{transcribe_result}")

        os.remove(temp_audio_path)
        logging.info(f"删除临时音频文件：{temp_audio_path}")

        return transcribe_result['segments']
    except Exception as e:
        logging.error(f"转录音频段时发生错误：{e}")
        return []


def transcribe_audio_to_srt(audio_path, output_srt_path, model_name="medium", gain=5.0):
    try:
        model = whisper.load_model(model_name)  # 使用参数化的模型名
        logging.info(f"Whisper {model_name} 模型已加载。")

        audio = AudioSegment.from_file(audio_path, format="mp3")
        length = len(audio)
        logging.info(f"音频文件 {audio_path} 已加载。长度：{length} 毫秒。")

        with open(output_srt_path, 'w', encoding='utf-8'):
            pass  # 初始化 SRT 文件

        segment_duration = 60 * 1000  # 尝试 60 秒

        with tempfile.TemporaryDirectory() as temp_dir:
            logging.info(f"创建临时目录：{temp_dir}")

            for i in range(0, length, segment_duration):
                start_time = i
                end_time = min(i + segment_duration, length)

                segment_audio = audio[start_time:end_time]
                segment_audio = segment_audio.apply_gain(5.0)  # 增加 5 dB 的音量

                segments = transcribe_segment(model, segment_audio, start_time, end_time, temp_dir, gain)
                update_srt_file(output_srt_path, segments, start_time)

        logging.info(f"删除临时目录：{temp_dir}")
    except Exception as e:
        logging.error(f"转录音频到 SRT 时发生错误：{e}")


def process_all_mp3_files_in_directory(directory_path, model_name="medium", gain=5.0):
    for filename in os.listdir(directory_path):
        if filename.endswith('.mp3'):
            full_audio_path = os.path.join(directory_path, filename)
            output_srt_path = full_audio_path + '.srt'
            logging.info(f"开始处理音频文件：{full_audio_path}")
            transcribe_audio_to_srt(full_audio_path, output_srt_path, model_name, gain)  # 直接在主线程中处理

    logging.info("所有音频文件处理完成。")



# 示例用法：
directory_path = r'G:\ceshi'  # 更改为你的目录路径
model_name = "medium"  # 或 "medium", "small" 根据资源选择
gain = 5.0  # 可以调整音量增益
process_all_mp3_files_in_directory(directory_path, model_name, gain)
