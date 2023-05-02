import os
import hashlib
import random
import yaml
from typing import Union, Optional
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
    def __init__(self, char: str, meanings: list[str], examples: list[dict[str, list[tuple[int, int]]]], weights: list[float]):
        self.char = char
        self.meanings = meanings
        self.examples = examples
        self.weights = weights

    def __getitem__(self, key):
        return self.meanings[key]

    def Weight(self, index: int) -> float:
        if index >= len(self.meanings):
            raise IndexError("Index out of range: " + str(index))
        while index >= len(self.weights):
            self.weights.append(1.0)
        return self.weights[index]

    def Choose(self, index: int):
        if index >= len(self.meanings):
            raise IndexError("Index out of range: " + str(index))
        while index >= len(self.weights):
            self.weights.append(1.0)
        self.weights[index] = max(0.0, self.weights[index] - 0.3)
        for i, v in enumerate(self.weights):
            if i != index:
                self.weights[i] = max(10.0, v + 0.1)
        return self[index]


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
            data.update(loaded_data)  # type: ignore
        else:
            data.extend(loaded_data)  # type: ignore
    return data


class WordDict:
    __dict: dict[str, dict[str, CcWord]]

    def __init__(self, poems: dict, weights: dict[str, list[float]], word_dict: Optional[dict] = None, path: str = words_path):
        def find_sentence_in_poems(sentence: str, poem: Poem) -> tuple[int, int]:
            for idx, line in enumerate(poem.Content):
                if sentence == line:
                    return idx, 0
            raise ValueError(
                f'Cannot find sentence "{sentence}" in poem "{poem.Title}"')

        def load_word_file(file_path: str):
            words = []
            _words = load_yaml(file_path)
            for word in _words:
                for i, ex in enumerate(word['examples']):
                    word['examples'][i] = {k: [eval(x) if x[0] == "(" else find_sentence_in_poems(
                        x, poems[k]) for x in v] for k, v in ex.items()}
                    word['weights'] = weights.get(
                        word['char'], [1.0] * len(word['examples']))
                words.append(CcWord(**word))
            return words

        t = []
        if not word_dict is None:
            t.extend(word_dict.values())
        else:
            t.extend(load_data(path, load_word_file, False))

        self.__dict = {x: {} for x in '0123456789abcdef'}
        for words in t:
            self.append(words)

    def save(self, path: str = words_path):
        def save_words(list_w: dict[str, CcWord], path: str):
            dicts = []
            for _word in list_w.values():
                word = {
                    'char': _word.char,
                    'meanings': _word.meanings,
                    'examples': _word.examples,
                }
                for i, ins in enumerate(word['examples']):
                    word['examples'][i] = {
                        k: [f'({x[0]},{x[1]})' for x in v] for k, v in ins.items()}
                dicts.append(word)
            save_yaml(dicts, path)
        for t, words in self.__dict.items():
            save_words(words, os.path.join(path, f'words_{t}.yaml'))
        save_weights(list(self.values()), path)

    def append(self, word: CcWord):
        if word.char in self:
            raise ValueError(f'Word "{word.char}" already exists')
        self.__dict[hashlib.sha1(word.char.encode()).hexdigest()[
            0]][word.char] = word

    def __getitem__(self, char: str):
        return self.__dict[hashlib.sha1(char.encode()).hexdigest()[0]][char]

    def __iter__(self):
        return iter(self.__dict.values())

    def __len__(self):
        return sum(len(x) for x in self.__dict.values())

    def __contains__(self, char: str):
        return char in self.__dict[hashlib.sha1(char.encode()).hexdigest()[0]]

    def __str__(self):
        return str(self.__dict)

    def __repr__(self):
        return repr(self.__dict)

    def values(self):
        for x in self.__dict.values():
            yield from x.values()


def load_poems(path: str, weights: dict) -> dict:
    def load_poem_file(file_path: str, weights: dict):
        poems = {}
        _poems = load_yaml(file_path)
        for p in _poems:
            p['Weight'] = weights.get(p['Title'], 1.0)
            poems[p['Title']] = Poem(**p)
        return poems
    return load_data(path, load_poem_file, True, weights)  # type: ignore


def load_questions(path: str, poems: dict, weights: dict) -> list[CompreQuestion]:
    """ 加载题目 """
    def load_question_file(file_path: str, poems: dict, weights: dict):
        questions = []
        _question_data = load_yaml(file_path)
        for qd in _question_data:
            qd['poems'] = [poems[t] for t in qd['poems']]
            qd['weight'] = weights.get(hashlib.sha1(
                qd['question'].encode()).hexdigest(), 1.0)
            if 'answers_str' in qd:
                qd['answers'] = qd.get('answers', [])
                qd['answers'].extend(
                    [[]] * (len(qd['answers_str']) - len(qd['answers'])))
                for i, answer_str in enumerate(qd['answers_str']):
                    if answer_str != []:
                        try:
                            qd['answers'][i] = [l.pop() for l in (
                                [idx for idx, str in enumerate(qd['poems'][i]) if str == x] for x in answer_str)]
                        except Exception as x:
                            print(f"{file_path}: {qd}")
                            raise x
                del qd['answers_str']
            questions.append(CompreQuestion(**qd))
        return questions
    result = load_data(path, load_question_file, False, poems, weights)
    if isinstance(result, list):
        return result
    else:
        raise TypeError(f"Expected list, got {type(result)}")


def draw_questions(questions: list[CompreQuestion], num: int) -> list[Question]:
    chosen_questions, seen_questions = [], set()

    def select_question():
        total_weight = sum(q.Weight()
                           for q in questions if q not in seen_questions)
        rw = random.uniform(0, total_weight)
        for question in questions:
            rw -= question.Weight()
            if question in seen_questions:
                continue
            if rw <= 0:
                return question
    for question in questions:
        question.weight = min(99.9, question.weight *
                              1.1, question.weight) + 0.1
    for _ in range(num):
        cq = select_question()
        if cq is None:
            continue
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
        weights = {hashlib.sha1(
            q.question.encode()).hexdigest(): q.weight for q in list_p}
    elif isinstance(list_p[0], Poem):
        weights = {p.Title: p.Weight for p in list_p}
    elif isinstance(list_p[0], CcWord):
        weights = {w.char: w.weights for w in list_p}
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


def gene_word_question(q: CompreQuestion, index: int, m: dict) -> list[WordQuestion]:
    w = sum(poem.Weight for poem in q.poems) or 0.001
    question_str = '在第{0}题中，第{1}空的"{2}"(第{3}个)的意思是：______________________。'
    t = [(sum([len(x) for x in q.answers[:a]]) + e, d)
         for a, b in enumerate(q.answers) if q.poems[a].Title in m
         for e, c in enumerate(b) if c in m[q.poems[a].Title]
         for d in m[q.poems[a].Title][c]]
    count = min(sum(1 for _ in range(len(t))
                if random.uniform(0, w * 5) < w), len(t))
    w = [w.Weight(c) for _, (w, c, _) in t]

    chosen_words, seen_words = [], set()

    def select_words():
        total_weight = sum(w)
        rw = random.uniform(0, total_weight)
        for i, _word in enumerate(t):
            rw -= w[i]
            if _word in seen_words:
                continue
            if rw <= 0:
                return _word
    for _ in range(count):
        a = select_words()
        chosen_words.append(a)
        seen_words.add(a)

    return [] if w == [] else [WordQuestion(question=question_str.format(index, i + 1, word.char, z + 1),
                                            answer=word.Choose(c),
                                            weight=0) for i, (word, c, z) in chosen_words]


def main():
    poems = load_poems(poems_path, load_weights(poems_path))
    questions = load_questions(
        questions_path, poems, load_weights(questions_path))
    words_dict = WordDict(poems, load_weights(words_path))

    type_code = int(
        input("0: 理解性默写（带字词考察）\n1: 理解性默写（不带字词考察）\n2: 字词考察\n请输入题目的类型：") or 0)
    num = int(input('请输入抽取题目的数量：'))

    if num == -1:
        counts = {pt: sum(1 for q in questions if pt in [t.Title for t in q.poems]) for pt in [
            poem.Title for poem in poems.values()]}
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
            word_questions = gene_word_question(
                question, i + 1, poem_words)  # type: ignore
            chosen_questions.extend(word_questions)

    with open('output.txt', 'w', encoding='utf-8') as output_file:
        for idx, question in enumerate(chosen_questions):
            output_file.write(f'{idx + 1}. {question.question}\n')
        output_file.write('\n')
        for idx, question in enumerate(chosen_questions):
            output_file.write(f'{idx + 1}. {question.Answers()}\n')

    save_weights(questions, questions_path)
    save_weights(list(poems.values()), poems_path)
    save_weights(list(words_dict.values()), words_path)


if __name__ == '__main__':
    main()
