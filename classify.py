from main import *

if __name__ == '__main__':
    poems = load_poems(poems_path, load_weights(poems_path))
    questions = load_questions(questions_path, poems, load_weights(questions_path))
    # 给 questions 排序
    questions.sort(key=lambda x: x.answers[0])
    save_questions(questions, questions_path)
    WordDict(poems, load_weights(words_path)).save()