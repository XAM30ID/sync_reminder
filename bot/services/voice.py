import os
import speech_recognition as sr
from pydub import AudioSegment

def convert_ogg_to_wav(ogg_path: str) -> str:
    """Конвертация .ogg файла в .wav для распознавания"""
    wav_path = ogg_path.replace('.ogg', '.wav')
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format='wav')
    return wav_path

def transcribe_audio(file_path: str) -> str:
    """Преобразование голосового сообщения в текст"""
    try:
        # Конвертируем в WAV для speech_recognition
        wav_path = convert_ogg_to_wav(file_path)
        
        # Инициализируем распознаватель
        recognizer = sr.Recognizer()
        
        # Загружаем аудиофайл
        with sr.AudioFile(wav_path) as source:
            # Читаем аудио данные
            audio_data = recognizer.record(source)
            
            # Распознаем текст (используем русский язык)
            text = recognizer.recognize_google(audio_data, language='ru-RU')
            return text
            
    except sr.UnknownValueError:
        print("Speech Recognition could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Speech Recognition service; {e}")
        return None
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None
    finally:
        # Очистка временных файлов
        try:
            os.remove(file_path)  # Удаляем оригинальный .ogg файл
            if file_path.endswith('.ogg'):
                wav_path = file_path.replace('.ogg', '.wav')
                if os.path.exists(wav_path):
                    os.remove(wav_path)  # Удаляем временный .wav файл
        except:
            pass 