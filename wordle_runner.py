from enum import Enum

from wordle_helper import WordleHelper, ScoringMethod
import pandas as pd


class Mode(Enum):
    HUMAN = "HUMAN"
    BACKTESTING = "BACKTESTING"


class WordleRunner:
    def __init__(self,
                 mode: Mode = Mode.HUMAN,
                 _scoring_method: ScoringMethod = ScoringMethod.LATER_POPULARITY):
        self.wordle_helper = WordleHelper(_scoring_method)
        self.mode = mode
        self.num_moves = 0
        self.smart_move_override = -1
        self.res_file_location = 'performance.txt' if mode == Mode.HUMAN else f'backtesting_{_scoring_method.value}.txt'
        self.backtesting_word = None

    def reset_game(self):
        self.num_moves = 0
        self.smart_move_override = -1
        self.backtesting_word = None
        self.wordle_helper.reset_game()

    def run_program(self):
        if self.mode == Mode.HUMAN:
            self.run_game_mode()
        else:
            self.run_backtesting()

    def run_backtesting(self):
        words_df = pd.read_csv('5_letter_words.txt', header=None, names=['word'])
        word_list = list(words_df['word'])
        word_list = ['hazes']
        for word in word_list:
            self.backtesting_word = word
            game_unfinished = True
            while game_unfinished:
                game_unfinished = self.run_next_move_instance()
            self.reset_game()

    def run_game_mode(self):
        while True:
            game_unfinished = True
            while game_unfinished:
                game_unfinished = self.run_next_move_instance()

            continue_game = input("Continue another game? [Y/N]: ")
            if continue_game in ["N", "n"]:
                break
            self.reset_game()

    def get_feedback_for_backtesting(self) -> str:
        if self.backtesting_word is None:
            return "xxxxx"

        feedback_list = ['x' for _ in range(5)]
        correct_pos_list = set()
        for i in range(5):
            if self.wordle_helper.last_suggestion[i] == self.backtesting_word[i]:
                feedback_list[i] = 'g'
                correct_pos_list.add(self.backtesting_word[i])

        for i in range(5):
            if self.wordle_helper.last_suggestion[i] not in self.backtesting_word:
                feedback_list[i] = 'x'
            elif self.wordle_helper.last_suggestion[i] not in correct_pos_list:
                feedback_list[i] = 'o'
        feedback_str: str = "".join(feedback_list)
        print(f"Feedback: {feedback_str}")
        return feedback_str

    def run_next_move_instance(self):
        if self.smart_move_override >= 0:
            print(f"[SMART MODE] pos={self.smart_move_override}")
            word_suggestion = self.wordle_helper.suggest_smart_move(self.smart_move_override)
        else:
            word_suggestion = self.wordle_helper.suggest_next_move()
        print(f"SUGGESTION: {word_suggestion}")
        if word_suggestion is None or word_suggestion in self.wordle_helper.suggestion_set:
            res_file = open(self.res_file_location, 'a')
            res_file.write(f"{self.backtesting_word}, {-1}, {self.wordle_helper.scoring_method.value} \n")
            res_file.close()
            return False
        else:
            self.wordle_helper.suggestion_set.add(word_suggestion)

        self.num_moves += 1
        self.wordle_helper.update_move_num(self.num_moves)

        word_feedback_list: str = "xxxxx"
        if self.mode == Mode.HUMAN:
            feedback_correct = False
            while not feedback_correct:
                word_feedback_list = input("Input feedback [x: char-not-present, o: incorrect-pos, "
                                           "g: correct-pos]: ")
                if len(word_feedback_list) != 5 \
                        or any(feedback_val not in ['x', 'o', 'g'] for feedback_val in word_feedback_list):
                    feedback_correct = False
                else:
                    feedback_correct = True
        else:
            word_feedback_list = self.get_feedback_for_backtesting()

        missing_chars, missing_pos = self.wordle_helper.get_missing_chars_pos()
        for i in range(5):
            if word_feedback_list[i] == 'g' and self.wordle_helper.correct_char_pos_map[i] is '':
                self.wordle_helper.correct_char_pos_map[i] = self.wordle_helper.last_suggestion[i]
            elif word_feedback_list[i] == 'o' and missing_chars == 1 \
                    and self.wordle_helper.last_suggestion[i] not in self.wordle_helper.correct_char_pos_map:
                self.wordle_helper.correct_char_pos_map[missing_pos] = self.wordle_helper.last_suggestion[i]

        missing_chars, missing_pos = self.wordle_helper.get_missing_chars_pos()

        # print(f"Pos-map: {self.correct_char_pos_map}")
        if missing_chars == 0:
            print(f"Congrats! Num-suggestions needed: {self.num_moves}")
            res_file = open(self.res_file_location, 'a')
            game_word = "".join(self.wordle_helper.correct_char_pos_map)
            res_file.write(f"{game_word}, {self.num_moves}, {self.wordle_helper.scoring_method.value} \n")
            res_file.close()
            return False

        self.wordle_helper.input_suggestion_feedback(word_feedback_list)

        if len(self.wordle_helper.word_score_map) == 0:
            res_file = open(self.res_file_location, 'a')
            game_word = "".join(self.wordle_helper.correct_char_pos_map)
            res_file.write(f"{game_word}, {-1}, {self.wordle_helper.scoring_method.value} \n")
            res_file.close()
            return False

        if missing_chars == 1 and len(self.wordle_helper.word_score_map) > 2:
            self.smart_move_override = missing_pos

        return True


# for score_method in ScoringMethod:
#     wordle_runner = WordleRunner(Mode.BACKTESTING, score_method)
#     wordle_runner.run_program()
wordle_runner = WordleRunner(Mode.BACKTESTING, ScoringMethod.LATER_POPULARITY)
wordle_runner.run_backtesting()
