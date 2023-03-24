from main import *

if __name__ == '__main__':
    save_questions(load_questions(questions_path, load_poems(poems_path, load_weights(poems_path)), load_weights(questions_path)), questions_path)
    save_words(load_words(words_path), words_path)