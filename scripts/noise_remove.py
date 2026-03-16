import librosa
import noisereduce as nr

def remove_noise(input_file, output_file):
    y, sr = librosa.load(input_file, sr=None)
    noise_sample = y[:int(sr * 0.5)]  # Use first half second for noise profile
    reduced_noise = nr.reduce_noise(y=y, sr=sr, y_noise=noise_sample)
    librosa.output.write_wav(output_file, reduced_noise, sr)

if __name__ == '__main__':
    import sys
    remove_noise(sys.argv[1], sys.argv[2])
