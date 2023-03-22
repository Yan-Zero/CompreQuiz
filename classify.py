from main import *

if __name__ == '__main__':
    save_questions(load_questions(questions_path, load_poems('Resources/remember/chinese/poem/'), load_weights(questions_path)), questions_path)