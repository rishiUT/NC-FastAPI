import whisper
import os
import time
import json

input_folder_prefix = "first_negotiation_"
conv_folder = "conversations-first-negotiation/"
transcript_folder = "conv_transcripts_fn/"

with open('static/filtered_train.json') as item_file:
    items = json.load(item_file)

def strip_file(filename: str):
    model = whisper.load_model("medium.en")
    input_filename = conv_folder + filename
    output_filename = transcript_folder + filename
    file1 = open(input_filename, 'r')
    file2 = open(output_filename, 'w+')
    lines = file1.readlines()

    title = lines[0].strip()
    item_num = lines[1].strip()
    item_id = item_num.split("item ", 1)

    buyer_id = lines[2].strip()
    seller_id = lines[3].strip()

    item_data = items[int(item_id[1])]
    price = item_data['Price']
    buyer_goal = price * 0.8
    price = "Seller Goal = " + str(price)
    file2.write(price)
    file2.write("\n")
    price = "Buyer Goal = " + str(buyer_goal)
    file2.write(price)
    file2.write("\n")
    description = item_data['Description'][0]
    file2.write(description)
    file2.write("\n")
    image = "/static/images/" + item_data['Images'][0]
    file2.write(image)
    file2.write("\n")

    speakers = ["buyer: ", "seller: "]
    num_messages = len(lines) - (4 + 2)
    num_turns = 0
    num_tokens = 0
    vocab = dict()
    for message_num in range(num_messages):
        speaker = speakers[message_num % 2]
        line_num = message_num + 4
        message = lines[line_num].strip()
        message_file = message.split("file ", 1)
        message_file = input_folder_prefix + message_file[1]
        print(message_file)
        result = model.transcribe(message_file)
        file2.write(speaker + result["text"])
        file2.write("\n")
        line = result["text"]
        num_turns += 1
        for word in line.split():
            norm_word = f_normalize(word)
            if word != "":
                if norm_word in vocab:
                    vocab[norm_word] += 1
                else:
                    vocab[norm_word] = 1
                num_tokens += 1 
    to_write = "Average number of tokens per turn: " + str(num_tokens / num_turns) + "\n"
    file2.write(to_write)
    to_write = "Vocab Size: " + str(len(vocab)) + "\n"
    file2.write(to_write)

    amount = lines[num_messages + 4].strip()
    accepted = lines[num_messages + 4 + 1].strip()

def transcribe_files():
    for filename in sorted(os.listdir(conv_folder)):
        print(filename)
        strip_file(filename)

def f_normalize(word: str):
    result = ""
    for char in word:
        if char.isalnum():
            result += char

    return result.lower()

def f_normalize_no_nums(word: str):
    result = ""
    for char in word:
        if char.isalpha():
            result += char

def get_file_avg_tokens(input_filename, normalize=f_normalize):
    vocab = dict()
    num_tokens = 0
    num_turns = 0
    file1 = open(input_filename, 'r')
    for line in file1:
        num_turns += 1
        for word in line.split():
            norm_word = normalize(word)
            if word != "":
                if norm_word in vocab:
                    vocab[norm_word] += 1
                else:
                    vocab[norm_word] = 1
                num_tokens += 1 
    return len(vocab), num_tokens / num_turns

def get_avg_tokens(normalize):
    vocab = dict()
    num_tokens = 0
    num_turns = 0
    for filename in sorted(os.listdir(transcript_folder)):
        input_filename = transcript_folder + filename
        file1 = open(input_filename, 'r')
        for line in file1:
            num_turns += 1
            for word in line.split():
                norm_word = normalize(word)
                if word != "":
                    if norm_word in vocab:
                        vocab[norm_word] += 1
                    else:
                        vocab[norm_word] = 1
                    num_tokens += 1 
    print(vocab)
    return len(vocab), num_tokens / num_turns

    return result.lower()

transcribe_files()
# print(get_avg_tokens(f_normalize))
# print(get_avg_tokens(f_normalize_no_nums))