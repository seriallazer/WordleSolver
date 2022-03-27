from enum import Enum
from math import sqrt
from collections import OrderedDict, Counter
from typing import List, Dict, Tuple

import matplotlib as plt
import numpy
import pandas as pd


class ScoringMethod(Enum):
    WORD_CHAR_SCORE = "WORD_CHAR_SCORE"
    TF_SCORE = "TF_SCORE"
    MOVES_BASED_INTERPOLATION = "MOVES_BASED_INTERPOLATION"
    MOVES_BASED_INTERPOLATION_SQRT = "MOVES_BASED_INTERPOLATION_SQRT"
    LATER_POPULARITY = "LATER_POPULARITY"


class WordScore:
    def __init__(self, word: str, word_score: float, tf_score: float,
                 scoring_method: ScoringMethod = ScoringMethod.LATER_POPULARITY):
        self.word, self.word_score, self.tf_score = word, word_score, tf_score
        self.move_num = 0
        self.MAX_MOVES = 6
        self.scoring_method = scoring_method
        self.score = self.get_score()

    def get_score(self) -> float:
        if self.scoring_method == ScoringMethod.WORD_CHAR_SCORE:
            return self.word_score
        elif self.scoring_method == ScoringMethod.TF_SCORE:
            return self.tf_score
        elif self.scoring_method == ScoringMethod.MOVES_BASED_INTERPOLATION:
            return self.get_score_MOVE_BASED_INTERPOLATION()
        elif self.scoring_method == ScoringMethod.MOVES_BASED_INTERPOLATION_SQRT:
            return self.get_score_MOVE_BASED_INTERPOLATION_SQRT()

        return self.get_score_LATER_POPULARITY()

    def get_score_MOVE_BASED_INTERPOLATION_SQRT(self) -> float:
        if self.tf_score < 0.001:
            return 0
        a, b = sqrt(max(self.MAX_MOVES - self.move_num, 0)), sqrt(min(self.move_num, 6))
        return ((a * self.word_score) + (b * self.tf_score)) / (a + b)

    def get_score_MOVE_BASED_INTERPOLATION(self) -> float:
        if self.tf_score < 0.001:
            return 0
        a, b = max(self.MAX_MOVES - self.move_num, 0), min(self.move_num, 6)
        return ((a * self.word_score) + (b * self.tf_score)) / (a + b)

    def get_score_LATER_POPULARITY(self) -> float:
        if self.tf_score < 0.001:
            return 0
        return (self.word_score / (1 << self.move_num)) + self.tf_score

    def __lt__(self, other):
        if self.score > other.score:
            return True
        if self.score == other.score and self.tf_score > other.tf_score:
            return True
        if self.score == other.score and self.tf_score == other.tf_score \
                and self.word_score > other.word_score:
            return True
        return False

    def __str__(self):
        return f"[{self.word}->{self.score},{self.tf_score},{self.word_score}]"


class WordleHelper:
    def __init__(self, scoring_method: ScoringMethod = ScoringMethod.LATER_POPULARITY):
        # self.word_list = WordleHelper.get_word_list()
        # self.freq_map = WordleHelper.create_initial_word_score_map(self.word_list)
        self.scoring_method = scoring_method
        self.org_word_score_map: List[WordScore] = self.create_initial_word_score_map()
        self.word_score_map = self.org_word_score_map.copy()
        self.correct_char_list_map = {}
        self.incorrect_pos_list = {}
        self.wrong_char_list = set()
        self.last_suggestion = None
        self.correct_char_pos_map: List[str] = ['' for _ in range(5)]
        self.suggestion_set = set()

    def reset_game(self):
        self.word_score_map = self.org_word_score_map.copy()
        self.correct_char_list_map = {}
        self.incorrect_pos_list = {}
        self.wrong_char_list = set()
        self.last_suggestion = None
        self.correct_char_pos_map: List[str] = ['' for _ in range(5)]
        self.suggestion_set = set()

    def update_move_num(self, num_moves: int):
        for word_score in self.word_score_map:
            word_score.move_num = num_moves
            word_score.score = word_score.get_score()
        self.word_score_map.sort()

    def get_missing_chars_pos(self) -> Tuple[int, int]:
        missing_chars, missing_pos = 0, -1
        for i in range(len(self.correct_char_pos_map)):
            if self.correct_char_pos_map[i] is '':
                missing_chars += 1
                missing_pos = i
        return missing_chars, missing_pos

    def suggest_smart_move(self, rhyming_pos: int) -> str:
        trial_letters = set()
        for word_score in self.word_score_map:
            word, score = word_score.word, word_score.score
            if all(self.last_suggestion[i] == word[i] for i in range(5) if i != rhyming_pos):
                trial_letters.add(word[rhyming_pos])

        print(f"Trial-letters: {trial_letters}")

        if len(trial_letters) == 1:
            mchar = next(iter(trial_letters))
            mword = [xch for xch in self.last_suggestion]
            mword[rhyming_pos] = mchar
            self.last_suggestion = "".join(mword)
            return self.last_suggestion

        trial_word_map_list = []
        for word_score in self.org_word_score_map:
            word = word_score.word
            if word in self.suggestion_set:
                continue
            num_trial_letters = sum([1 if tletter in word else 0 for tletter in trial_letters])
            for tletter in trial_letters:
                if tletter in self.last_suggestion \
                        and tletter in word \
                        and word[rhyming_pos] != tletter:
                    num_trial_letters -= 1
            if num_trial_letters > 0:
                trial_word_map_list.append([word, num_trial_letters, word_score])

        if not trial_word_map_list:
            return self.suggest_next_move()

        trial_word_map_list.sort(key=lambda x: x[1], reverse=True)
        print(f"#Smart words = {len(trial_word_map_list)} || Details: {trial_word_map_list[0][2]}")
        # print(trial_word_map_list[:20])
        self.last_suggestion = trial_word_map_list[0][0]
        return self.last_suggestion

    def suggest_next_move(self) -> str:
        suggestion, suggestion_class = None, None
        remove_words = set()
        for word_score in self.word_score_map:
            word, score = word_score.word, word_score.score
            if self.wrong_char_list and any(wchar in word for wchar in self.wrong_char_list):
                remove_words.add(word)
                continue
            correct_pos_satisfied = True
            for cchar, pos_list in self.correct_char_list_map.items():
                for pos in pos_list:
                    if word[pos] != cchar:
                        correct_pos_satisfied = False
            if not correct_pos_satisfied:
                remove_words.add(word)
                continue

            incorrect_pos_satisfied = True
            for ichar, pos_list in self.incorrect_pos_list.items():
                for pos in pos_list:
                    if word[pos] == ichar:
                        incorrect_pos_satisfied = False
            if not incorrect_pos_satisfied:
                remove_words.add(word)
                continue

            if self.incorrect_pos_list and any(ichar not in word for ichar in self.incorrect_pos_list.keys()):
                remove_words.add(word)
                continue

            if suggestion is None:
                suggestion = word
                suggestion_class = word_score
                remove_words.add(word)

        self.word_score_map = [wc for wc in self.word_score_map if wc.word not in remove_words]
        print([wc.__str__() for wc in self.word_score_map[:10]])
        self.last_suggestion = suggestion
        print(f"Remaining words in suggester: {len(self.word_score_map)} || Details: {suggestion_class}")
        return suggestion

    # Feedback list-values: [-1: char missing, 0: incorrect-pos, 1: correct-pos]
    def input_suggestion_feedback(self, feedback_list: str):
        char_pos_feedback_map = {}
        for i in range(len(feedback_list)):
            if feedback_list[i] in ['o', 'g']:
                char_pos_feedback_map[self.last_suggestion[i]] = (feedback_list[i], i)

        for i in range(len(feedback_list)):
            if feedback_list[i] == 'x' and self.last_suggestion[i] not in char_pos_feedback_map:
                char_pos_feedback_map[self.last_suggestion[i]] = ('x', i)

        for char, feedback_tuple in char_pos_feedback_map.items():
            feedback, pos = feedback_tuple
            if feedback == 'g':
                if char not in self.correct_char_list_map:
                    self.correct_char_list_map[char] = set()
                self.correct_char_list_map[char].add(pos)
            elif feedback == 'o':
                if char not in self.incorrect_pos_list:
                    self.incorrect_pos_list[char] = set()
                self.incorrect_pos_list[char].add(pos)
            else:
                self.wrong_char_list.add(char)

    @staticmethod
    def get_word_list() -> pd.DataFrame:
        df = pd.read_csv('5_letter_words.txt', header=None, names=['word'])
        return df

    @staticmethod
    def create_char_freq_map(word_list: List[str]) -> Dict[str, List[float]]:
        fmap = {}
        for i in range(26):
            cval = chr(ord('a') + i)
            fmap[cval] = [0 for _ in range(6)]

        for word in word_list:
            wcounter = Counter(word)
            for wchar, cfreq in wcounter.items():
                fmap[wchar][cfreq] += 1

        for char_key in fmap:
            for j in range(len(fmap[char_key])):
                fmap[char_key][j] = (100.0 * fmap[char_key][j]) / len(word_list)
        return fmap

    def create_initial_word_score_map(self) -> List[WordScore]:
        wdf: pd.DataFrame = pd.read_csv('5_letter_words.txt', header=None, names=['word'])
        wiki_df: pd.DataFrame = pd.read_csv('word_freq_wikipedia.csv')
        wiki_df = wiki_df[wiki_df.word.str.len() == 5]
        wiki_df.to_csv('word_freq_wikipedia.csv', index=False)

        wiki_df['word'] = wiki_df['word'].str.lower()
        wiki_df = wiki_df.merge(wdf, how='inner', on='word')
        wiki_df.fillna({'count': 0}, inplace=True)

        max_count = sqrt(wiki_df['count'].max())
        wiki_df['sqrt_count'] = numpy.sqrt(wiki_df['count'])
        wiki_df['tf_score'] = (100.0 * wiki_df['sqrt_count']) / max_count

        char_freq_map = WordleHelper.create_char_freq_map(list(wiki_df['word']))

        def get_word_char_freq_score(word: str) -> int:
            wcounter = Counter(word)
            word_score = 0
            for wchar, cfreq in wcounter.items():
                mult = 1
                if wchar in "aeiou" and cfreq == 1:
                    mult = 2
                word_score += mult * char_freq_map[wchar][cfreq]
            return word_score

        wiki_df['char_freq_score'] = wiki_df['word'].map(get_word_char_freq_score)

        max_char_freq_score = wiki_df['char_freq_score'].max()
        wiki_df['char_freq_score'] = (100.0 * wiki_df['char_freq_score']) / max_char_freq_score

        wiki_df.to_csv('word_details.csv', index=False)

        score_map: List[WordScore] = []
        for index, row in wiki_df.iterrows():
            word_score = WordScore(word=row['word'], word_score=row['char_freq_score'],
                                   tf_score=row['tf_score'], scoring_method=self.scoring_method)
            score_map.append(word_score)

        score_map.sort()
        return score_map

    @staticmethod
    def _create_word_score_map(word_list: List[str], freq_map: Dict[chr, List[float]]) -> List[WordScore]:
        score_map = []
        for word in word_list:
            word_score = 0
            wcounter = Counter(word)
            for wchar, cfreq in wcounter.items():
                word_score += freq_map[wchar][cfreq]
            score_map.append(WordScore(word, word_score))
        score_map.sort()
        return score_map

