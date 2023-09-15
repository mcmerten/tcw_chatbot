"""
This script is used to test the generated responses and only a test. It is not used in the actual application.

Depending on the setup, the following steps are required:
1. export PYTHONPATH=$PYTHONPATH:/Users/merten/Development/tcw_chatbot/app/benchmark
2. from (venv) tcw_chatbot (virtual environment) in the bash run: % bench run app/benchmark/eval.py
"""

from benchllm import StringMatchEvaluator, Test, Tester

# Instantiate your Test objects
tests = [
    Test(input="Wie kann ich TCW kontaktieren?",
         expected=[
             "Sie können TCW unter der Nummer +49 89 360523-0 anrufen oder eine E-Mail an mail@tcw.de senden. Die Geschäftszeiten sind Montag bis Freitag von 08.30 bis 17.00 Uhr ([1](https://tcw.de/unternehmensberatung/sonstiges/impressum-150#3), [2](https://tcw.de/unternehmen/sonstiges/kontakt-170))."]),
]
# Use a Tester object to generate predictions using any test functions
tester = Tester(lambda _: 1)
tester.add_tests(tests)
predictions = tester.run()

# Use an Evaluator object to evaluate your model
evaluator = StringMatchEvaluator()
evaluator.load(predictions)
results = evaluator.run()
print(results)



