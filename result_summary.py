from wordle_helper import ScoringMethod
import pandas as pd

results = []

for score_method in ScoringMethod:
    resfile = f'backtesting_{score_method.value}.txt'
    df = pd.read_csv(resfile, header=None, names=['word', 'moves', 'smethod'])
    df = df[df.moves > 0]
    success_rate = (100.0 * len(df[df.moves < 7]))/len(df)
    avg_moves = df[df.moves < 7]['moves'].mean()
    results.append([score_method.value, success_rate, avg_moves])

print(results)