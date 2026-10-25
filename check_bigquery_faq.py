import requests

r = requests.get('https://httparchive.org/faq', timeout=30)
idx = r.text.find('how-do-i-use-bigquery')
if idx >= 0:
    # Find the answer section
    answer_start = r.text.find('<h2 id="how-do-i-use-bigquery', idx)
    if answer_start == -1:
        answer_start = r.text.find('<p>', idx)
    if answer_start > 0:
        next_h2 = r.text.find('<h2', answer_start + 1)
        if next_h2 > 0:
            print(r.text[answer_start:next_h2])
        else:
            print(r.text[answer_start:answer_start+5000])