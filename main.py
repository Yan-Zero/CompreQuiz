import os, hashlib, random, yaml
from typing import Union
from abc import ABC, abstractmethod

root_path = 'Resources/remember/chinese/'
questions_path = os.path.join(root_path, 'questions')
poems_path = os.path.join(root_path, 'poem')
words_path = os.path.join(root_path, 'words')

class Poem:
    def __init__(self, Title: str, Content: list[str], Weight: float):
        self.Title = Title
        self.Content = Content
        self.Weight = Weight

    def __getitem__(self, key):
        return self.Content[key]

class CcWord:
    def __init__(self, char: str, meanings: list[str], examples: list[dict[str, tuple[int, int]]]):
        self.char = char
        self.meanings = meanings
        self.examples = examples

    def __getitem__(self, key):
        return self.meanings[key]

class Question(ABC):
    def __init__(self, weight: float, question: str):
        self.weight = weight
        self.question = question
    @abstractmethod
    def Weight(self):
        pass
    @abstractmethod
    def Answers(self) -> str:
        pass

class WordQuestion(Question):
    def __init__(self, weight: float, question: str, answer: str):
        super().__init__(weight, question)
        self.answer = answer

    def Answers(self) -> str:
        return self.answer

    def Weight(self):
        return self.weight

class CompreQuestion(Question):
    def __init__(self, weight: float, question: str, answers: list[list[int]], poems: list[Poem]):
        super().__init__(weight, question)
        self.answers = answers
        self.poems = poems

    def Answers(self) -> str:
        return "; ".join([', '.join([self.poems[idy].Content[i] for i in answer]) for idy, answer in enumerate(self.answers)])

    def Weight(self):
        return self.weight * sum(poem.Weight for poem in self.poems) / len(self.poems)

def load_yaml(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file) or {}

def save_yaml(data, path: str):
    with open(path, 'w', encoding='utf-8') as file:
        yaml.dump(data, file, allow_unicode=True)

def load_data(path: str, loader_func, is_dict, *args):
    data = {} if is_dict else []
    for filename in os.listdir(path):
        if filename == 'weights.yaml':
            continue
        file_path = os.path.join(path, filename)
        loaded_data = loader_func(file_path, *args)
        if is_dict:
            data.update(loaded_data)
        else:
            data.extend(loaded_data)
    return data

def load_words(path: str) -> dict[str, CcWord]:
    def load_word_file(file_path: str):
        words = {}
        _words = load_yaml(file_path)
        for word in _words:
            for i, ex in enumerate(word['examples']):
                word['examples'][i] = {k: [eval(x) for x in v] for k, v in ex.items()}
            words[word['char']] = CcWord(**word)
        return words

    return load_data(path, load_word_file, True)

def save_words(list_w: dict[str, CcWord], path: str):
    dicts = {}
    for t, _word in list_w.items():
        word = _word.__dict__
        for i, ins in enumerate(word['examples']):
            word['examples'][i] = {k: [f'({x[0]},{x[1]})' for x in v] for k, v in ins.items()}
        t = next(x for x in word['examples'][0])
        if t not in dicts:
            dicts[t] = []
        dicts[t].append(word)
    for t, words in dicts.items():
        save_yaml(words, os.path.join(path, f'words_{t}.yaml'))

def load_poems(path: str, weights: dict):
    def load_poem_file(file_path: str, weights: dict):
        poems = {}
        _poems = load_yaml(file_path)
        for p in _poems:
            p['Weight'] = weights.get(p['Title'], 1.0)
            poems[p['Title']] = Poem(**p)
        return poems
    return load_data(path, load_poem_file, True, weights)

def load_questions(path: str, poems: dict, weights: dict) -> list[CompreQuestion]:
    def load_question_file(file_path: str, poems: dict, weights: dict):
        questions = []
        _question_data = load_yaml(file_path)
        for qd in _question_data:
            qd['poems'] = [poems[t] for t in qd['poems']]
            qd['weight'] = weights.get(hashlib.sha1(qd['question'].encode()).hexdigest(), 1.0)
            if 'answers_str' in qd:
                for i, answer_str in enumerate(qd['answers_str']):
                    if answer_str != []:
                        try:
                            qd['answers'][i] = [l.pop() for l in ([idx for idx, str in enumerate(qd['poems'][i]) if str == x] for x in answer_str)]
                        except Exception as x:
                            print(f"{file_path}: {qd}")
                            raise x
            questions.append(CompreQuestion(**qd))
        return questions
    return load_data(path, load_question_file, False, poems, weights)

def draw_questions(questions: list[CompreQuestion], num: int) -> list[Question]:
    chosen_questions, seen_questions = [], set()
    def select_question():
        total_weight = sum(q.Weight() for q in questions if q not in seen_questions)
        rw = random.uniform(0, total_weight)
        for question in questions:
            if question in seen_questions:
                continue
            rw -= question.Weight()
            if rw <= 0:
                return question
    for question in questions:
        question.weight = min(99.9, question.weight * 1.1, question.weight) + 0.1
    for _ in range(num):
        cq = select_question()
        chosen_questions.append(cq)
        seen_questions.add(cq)
        cq.weight = 0
        for poem in cq.poems:
            poem.Weight = max(0.001, poem.Weight - 0.5)
    return chosen_questions

def load_weights(path: str):
    return load_yaml(os.path.join(path, 'weights.yaml'))

def save_weights(list_p: list, path: str):
    if isinstance(list_p[0], Question):
        weights = {hashlib.sha1(q.question.encode()).hexdigest(): q.weight for q in list_p}
    elif isinstance(list_p[0], Poem):
        weights = {p.Title: p.Weight for p in list_p}
    else:
        raise TypeError
    save_yaml(weights, os.path.join(path, 'weights.yaml'))

def save_questions(questions: list[CompreQuestion], path: str):
    poem_questions = {question.poems[0].Title: [] for question in questions}
    for question in questions:
        poem_questions[question.poems[0].Title].append({
            'question': question.question, 'answers': question.answers,
            'poems': [x.Title for x in question.poems]})
    
    for poem_title, poem_questions_list in poem_questions.items():
        filename = f'question_{poem_title}.yaml'
        save_yaml(poem_questions_list, os.path.join(path, filename))
    
    save_weights(questions, path)

def gene_word_question(question: CompreQuestion, index: int, mapping: dict) -> list[WordQuestion]:
    weigth = sum(poem.Weight for poem in question.poems) or 0.001
    question_str = '在第{0}题中，第{1}空的"{2}"(第{3}个)的意思是：______________________。'
    t = [(a, c) for a, b in enumerate(question.answers) for c in b]
    count = min(sum(1 for _ in range(len(t)) if random.uniform(0, weigth * 10) < weigth), len(t))
    t = random.sample(list(enumerate(t)), k=count)
    
    return [WordQuestion(question=question_str.format(index, i + 1, word.char, z + 1),
                         answer=word[c],
                         weight=0) for i, (a, b) in t 
                         if question.poems[a].Title in mapping and b in mapping[question.poems[a].Title] for word, c, z in 
                         [random.choice(mapping[question.poems[a].Title][b])]]

def main():
    poems = load_poems(poems_path, load_weights(poems_path))
    words_dict = load_words(words_path)
    questions = load_questions(questions_path, poems, load_weights(questions_path))

    type_code = int(input("0: 理解性默写（带字词考察）\n1: 理解性默写（不带字词考察）\n2: 字词考察\n请输入题目的类型：") or 0)
    num = int(input('请输入抽取题目的数量：'))

    if num == -1:
        counts = {poem_title: sum(1 for question in questions if poem_title in question.poems) for poem_title in {poem.Title for poem in poems.values()}}
        for poem_title, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            print('{:\u3000<25s}\t{}'.format(poem_title, count))
        print('{:\u3000<25s}\t{}'.format("总计", len(questions)))
        return

    if type_code == 0:
        poem_words = {}
        for word in words_dict.values():
            for index, example in enumerate(word.examples):
                for title, c in example.items():
                    for line, start in c:
                        if title not in poem_words:
                            poem_words[title] = {}
                        if line not in poem_words[title]:
                            poem_words[title][line] = []
                        poem_words[title][line].append((word, index, start))

    for poem in poems.values():
        poem.Weight = min(5, poem.Weight + 0.5)
    chosen_questions = draw_questions(questions, num)

    if type_code == 0:
        for i, question in enumerate(chosen_questions):
            if not isinstance(question, CompreQuestion):
                continue
            word_questions = gene_word_question(question, i + 1, poem_words)
            chosen_questions.extend(word_questions)

    with open('output.txt', 'w', encoding='utf-8') as output_file:
        for idx, question in enumerate(chosen_questions):
            output_file.write(f'{idx + 1}. {question.question}\n')
        output_file.write('\n')
        for idx, question in enumerate(chosen_questions):
            output_file.write(f'{idx + 1}. {question.Answers()}\n')
    save_weights(questions, questions_path)
    save_weights(list(poems.values()), poems_path)
    save_words(words_dict, words_path)

if __name__ == '__main__':
    main()