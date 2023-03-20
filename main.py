import os
import random
import yaml

class Poem:
    Title: str
    Content: list[str]

    def __init__(self, Title: str, Content: list[str]):
        self.Title = Title
        self.Content = Content

class Question:
    weight: float
    question: str
    answers: list[list[int]]
    poems: list[Poem]

    def __init__(self, weight: float, question: str, answers: list[list[int]], poems: list[Poem]):
        self.weight = weight
        self.question = question
        self.answers = answers
        self.poems = poems

def load_poems(path: str):
    poems = {}
    for filename in os.listdir(path):
        with open(os.path.join(path, filename), 'r', encoding='utf-8') as file:
            _poem = yaml.safe_load(file)
            for poem in _poem:
                poems[poem['Title']] = Poem(**poem)
    return poems

def load_questions(path: str, poems: dict):
    questions = []
    for filename in os.listdir(path):
        if len(filename) < 8 or filename[0:8] != "question":
            continue
        with open(os.path.join(path, filename), 'r', encoding='utf-8') as file:
            _question_data = yaml.safe_load(file)
            for question_data in _question_data:
                question_data['poems'] = [poems[title] for title in question_data['poems']]
                questions.append(Question(**question_data))
    return questions

def draw_questions(questions: list[Question], num: int) -> list[Question]:
    chosen_questions = []
    seen_questions = set()

    for _ in range(num):
        while True:
            total_weight = sum(q.weight for q in questions if q not in seen_questions)
            random_weight = random.uniform(0, total_weight)
            chosen_question = None

            for question in questions:
                if question in seen_questions:
                    continue

                random_weight -= question.weight
                if random_weight <= 0:
                    chosen_question = question
                    break

            if chosen_question is not None:
                break

        chosen_questions.append(chosen_question)
        seen_questions.add(chosen_question)
        chosen_question.weight = max(0.09, chosen_question.weight * 0.82)

    for question in questions:
        question.weight *= 1.1
        question.weight = min(10, question.weight)
    
    return chosen_questions

def save_questions(questions: list[Question], path: str):
    poem_questions = {}
    for question in questions:
        if question.poems[0].Title not in poem_questions:
            poem_questions[question.poems[0].Title] = []
        poem_questions[question.poems[0].Title].append({
            'weight': question.weight,
            'question': question.question,
            'answers': question.answers,
            'poems': [x.Title for x in question.poems]
        })

    for poem_title, poem_questions_list in poem_questions.items():
        filename = f'question_{poem_title}.yaml'
        with open(os.path.join(path, filename), 'w', encoding='utf-8') as file:
            yaml.dump(poem_questions_list, file, encoding="utf-8", allow_unicode=True)

def main():
    poems_path = 'Resources/remember/chinese/poem/'
    questions_path = 'Resources/remember/chinese/questions/'

    poems = load_poems(poems_path)
    questions = load_questions(questions_path, poems)
    num = int(input('请输入抽取题目的数量：'))

    chosen_questions = draw_questions(questions, num)

    with open('output.txt', 'w', encoding='utf-8') as output_file:
        for idx, question in enumerate(chosen_questions):
            output_file.write(f'{idx + 1}. {question.question}\n')
        output_file.write('\n')
        for idx, question in enumerate(chosen_questions):
            answers_text = []
            for idy, answer in enumerate(question.answers):
                answers_text += [question.poems[idy].Content[i] for i in answer]
            output_file.write(f'{idx + 1}. {", ".join(answers_text)}\n')

    save_questions(questions, questions_path)


if __name__ == '__main__':
    main()