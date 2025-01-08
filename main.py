import os
import random
from prettytable import PrettyTable
import re
import time


def to_moodle_format(input_file_path, output_file):

    if not os.path.exists(input_file_path):
        print("Error, file not found")
        return

    #input_file = open(file_path, "r", encoding='utf-8-sig')
    input_file = open(input_file_path, "r")
    output_file = open(output_file, "w")
    

    score = -1
    counter = 0
    line_counter = 0
    sep_counter = 0
    tags = []
    inSpecificFeedback = False
    inGenericFeedback = False
    error = False

    separator = True
    for line in input_file:
        line_counter += 1

        if line.__contains__("="):
            line = line.replace("=", "\\=")
        if line.__contains__("{"):
            line = line.replace("{", "\\{")
        if line.__contains__("}"):
            line = line.replace("}", "\\}")

        if line[0] == '_':  # question case
            inSpecificFeedback = False
            inGenericFeedback = False
            if separator:  # check if there is a separator before current question
                separator = False  # set separator to False for future checks
                line = line.strip()
                question = line[1:-1]
                counter += 1

                if question[-1] == ':':  # add a space if there's a : as last character to avoid import errors
                    question = question + " "

                if not line[-1].isdigit():  # check if there's the number of correct answers
                    print(f"Error, number of correct answers missing at the line: {line_counter} in file {input_file_path}")
                    error = True
                    output_file.close()
                    os.remove(output_file.name)
                    break
                n_corr = int(line[-1])

                if n_corr > 1:  # divide the score by the number of correct answers
                    score = 100 / n_corr
                output_file.write(f"// question: {counter}  name: {question}\n")
                if len(tags) > 0:
                    output_file.write("// ")
                    for tag in tags:
                        output_file.write(f"[tag:{tag}] ")
                    output_file.write("\n")
                output_file.write(f"::{question}::[html]<p><strong>{question}</strong></p>" + '{\n')

            else:
                print(f"Error, missing separator before line: {line_counter}")
                error = True
                output_file.close()
                os.remove(output_file.name)
                break
        elif line[0] == '$':
            tags = line[1:].strip().split(",")
            tags = list(filter(lambda t: t != "", tags))

        elif line[0] == '*':  # right answer case
            inSpecificFeedback = False
            inGenericFeedback = False
            correct_answer = line[1:]
            if score != -1:
                output_file.write(f"\t~%{score:.5f}%[moodle]{correct_answer}")
            else:
                output_file.write(f"\t=[moodle]{correct_answer}")

        elif line[0] == '-':  # wrong answer case
            inSpecificFeedback = False
            inGenericFeedback = False
            wrong_answer = line[1:]
            output_file.write(f"\t~[moodle]{wrong_answer}")

        elif line[0] == '#':  # feedback answer case
            feedback = line[1:]
            inSpecificFeedback = False
            if not inGenericFeedback:
                output_file.write(f"\t####[moodle]{feedback}")
                inGenericFeedback = True
            else:
                output_file.write(f"\t{feedback}")

        elif line[0] == '@':
            feedback = line[1:]
            inGenericFeedback = False
            if not inSpecificFeedback:
                output_file.write(f"\t#[moodle]{feedback}")
                inSpecificFeedback = True
            else:
                output_file.write(f"\t{feedback}")

        elif line[0] == '+':  # t/f answer case
            inSpecificFeedback = False
            inGenericFeedback = False
            answer = line[1]
            if answer == 'T':
                output_file.write(f"\tTRUE\n")
            elif answer == 'F':
                output_file.write(f"\tFALSE\n")
            else:
                print("Error, wrong answer format")
                error = True

        elif line[0] == '%':  # end of question case
            inSpecificFeedback = False
            inGenericFeedback = False
            sep_counter += 1
            output_file.write("}\n\n")
            separator = True
            score = -1

        else:
            if len(line.strip()) > 0:  # case of formatting error, only if not empty line
                print(f"Error: missing symbol indicator at line {line_counter}\n\t{line}")
                error = True
                output_file.close()
                os.remove(output_file.name)
                break

    if not error:
        if sep_counter != counter:
            print(f"You missed the last separator")
            output_file.close()
            os.remove(output_file.name)
        else:
            print(f"You just created {counter} questions")

def create_files_with_questions(config):
    """
    Creates output files with distributed questions based on the configuration.
    """

    out_folder = "out"
    moodle_folder = "moodle"
    os.makedirs(out_folder, exist_ok=True)
    os.makedirs(moodle_folder, exist_ok=True)

    # 1. Concatenate all in files
    all_questions_text = ""
    for filename in os.listdir(config['in_folder']):
        in_filename = os.path.join(config['in_folder'], filename)
        if os.path.isfile(in_filename):
            try:
                with open(in_filename, 'r', encoding='utf-8') as f:
                    all_questions_text += f.read()
            except FileNotFoundError:
                print(f"Warning: Input file '{in_filename}' not found.")

    # 2. Parse questions from the concatenated text
    questions = parse_questions(all_questions_text, config['labels']['blacklist'])

    if not questions:
        print("No valid questions found in input files.")
        return

    # 3. Apply label weights and filter
    weighted_labels = []
    available_questions = []
    for q in questions:
        valid_labels = [label for label in q['labels']]
        if valid_labels:
            q['labels'] = valid_labels  
        available_questions.append(q)
        for label in valid_labels:
            weight = config['labels']['weights'].get(label, 1)  # Default weight is 1
            weighted_labels.extend([label] * weight)

    for banned in config['labels']['blacklist']:
        for q in available_questions:
            # print(q['labels'], banned)
            if banned in q['labels']:
                # print("removed question with label: ", banned)
                available_questions.remove(q)

        

    # for q in available_questions:
    #     print(q['labels'])
    if not available_questions:
        print("No questions available after filtering by blacklist.")
        return

    # 4. Prepare for distribution
    num_available_questions = len(available_questions)
    num_out_files = config['num_out_files']
    min_questions_per_file = config['questions_per_out']['min']
    max_questions_per_file = config['questions_per_out']['max']
    distribution_factor = config['distribution']
    repeat_questions = config['repeat']
    high_distribution = config['high_distribution']
    randomize_order = config['randomize_order']

    questions_in_files = [[] for _ in range(num_out_files)]
    remaining_questions = []
    used_questions = set()

    label_counts_desired = {}
    for label, constraints in config['labels'].get('constraints', {}).items():
        label_counts_desired[label] = {'min': constraints.get('min', 0), 'max': constraints.get('max', float('inf')), 'count': 0}

    # Helper function to check if adding a question violates label constraints
    def can_add_question(question, file_index):
        for label in question['labels']:
            if label in label_counts_desired:
                if label_counts_desired[label]['count'] + 1 > label_counts_desired[label]['max']:
                    return False
        return True

    # 5. Distribute questions

    if config['randomize_order']:
        random.seed(os.urandom(4))
        random.shuffle(available_questions)

    label_counts_per_file = [{} for _ in range(config['num_out_files'])]
    total_labels_per_file = [0] * config['num_out_files']

    for file_index in range(config['num_out_files']):
        while len(questions_in_files[file_index]) < config['questions_per_out']['max'] and available_questions:
            possible_questions = []
            for q_index, question in enumerate(available_questions):
                if not config['repeat_questions'] and question['original_text'] in used_questions:
                    continue

                # Check global label constraints
                can_add_global = True
                for label in question['labels']:
                    constraints = config['labels']['constraints'].get(label, {'min': 0, 'max': float('inf')})
                    if label_counts_desired.get(label, {'count': 0})['count'] + 1 > constraints['max']:
                        can_add_global = False
                        break
                if not can_add_global:
                    continue

                # Check per-file label constraints
                can_add_file = True
                for label in question['labels']:
                    label_constraints_file = config['labels']['constraints'].get(label, {'min': 0, 'max': float('inf')})
                    if label_counts_per_file[file_index].get(label, 0) + 1 > label_constraints_file['max']:
                        can_add_file = False
                        break
                if not can_add_file:
                    continue

                score = 0.5

                # Encourage meeting min constraints
                # for label in question['labels']:
                #     if label in label_counts_desired:
                #         constraints = config['labels']['constraints'].get(label, {'min': 0, 'max': float('inf')})
                #         count_label=0 
                #         for q in possible_questions:
                #             if label in q[0]['labels']:
                #                 count_label += 1
                        
                        # if count_label < constraints['min']*config['num_out_files']:
                        #     print("min constraint", label, constraints.get('min', 0), count_label)
                        #     score += 50
                        # if count_label > constraints['max']*config['num_out_files']:
                        #     print("max constraint", label, constraints.get('max', 0), count_label)
                        #     score -= random.random()*50



                # Apply label weights
                for label in question['labels']:
                    score += config['labels']['weights'].get(label, 1)

                # Apply distribution to balance labels
                if config['distribution'] > 0:
                    label_distribution_score = 0
                    for label in question['labels']:
                        avg_label_count = sum(f.get(label, 0) for f in label_counts_per_file) / config['num_out_files']
                        diff = avg_label_count - label_counts_per_file[file_index].get(label, 0)
                        label_distribution_score += config['distribution'] * diff*0.5
                    score += label_distribution_score

                    avg_total_labels = sum(total_labels_per_file) / config['num_out_files']
                    total_labels_diff = avg_total_labels - total_labels_per_file[file_index]
                    score += config['distribution'] * total_labels_diff *0.6

                if config['high_distribution']:
                    for label in question['labels']:
                        if label in config['labels']['weights'] and config['labels']['weights'][label] < 2:
                            score *= 1 + (config['high_distribution'] * 0.6)

                
                score += random.random()*10
                if score <0:
                    score += random.random()*20


                possible_questions.append((question, score, q_index))

            if possible_questions:
                best_question, best_score, original_index = max(possible_questions, key=lambda item: item[1])
                questions_in_files[file_index].append(best_question)
                if not config['repeat_questions']:
                    used_questions.add(best_question['original_text'])
                for label in best_question['labels']:
                    label_counts_desired[label] = label_counts_desired.get(label, {'count': 0})
                    label_counts_desired[label]['count'] += 1
                    label_counts_per_file[file_index][label] = label_counts_per_file[file_index].get(label, 0) + 1
                total_labels_per_file[file_index] += len(best_question['labels'])
                available_questions.pop(original_index)
            else:
                break

        # print(f"File {file_index + 1}: {len(available_questions)} questions {len(remaining_questions)}")

    remaining_questions.extend(available_questions)

    # 6. Ensure minimum questions per file and handle remaining
    for i in range(num_out_files):
        while len(questions_in_files[i]) < min_questions_per_file and remaining_questions:
            questions_in_files[i].append(remaining_questions.pop())

    # Any truly leftover questions go to "last_questions"
    if remaining_questions:
        with open(os.path.join(out_folder, "file_quiz_last_questions"), 'w', encoding='utf-8') as f_last:
            for q in remaining_questions:
                f_last.write(q['original_text'] + "\n")
        to_moodle_format(os.path.join(out_folder, "file_quiz_last_questions"), os.path.join(moodle_folder, "moodle_file_quiz_last_questions.txt"))


    # 7. Write questions to output files
    for i in range(num_out_files):
        out_filename = os.path.join(out_folder, "file_quiz_"+str(i + 1)+".txt")
        if randomize_order:
            random.shuffle(questions_in_files[i])
        with open(out_filename, 'w', encoding='utf-8') as f_out:
            for question in questions_in_files[i]:
                f_out.write(question['original_text'] + "\n")
        try:
            to_moodle_format(out_filename, os.path.join(moodle_folder, "moodle_file_quiz_"+str(i + 1)+".txt"))
        except Exception as e:
            print(f"Error converting to moodle format:{str(i + 1)} , {e} ")

    # 8. Print stats
    if config['print_stats']:
        print("\n--- General Statistics ---")
        print(f"Total questions processed: {len(questions)}")
        print(f"Number of output files created: {num_out_files}")
        for i in range(num_out_files):
            print(f"File '{i + 1}': {len(questions_in_files[i])} questions")
        if remaining_questions:
            print(f"Questions in 'last_questions': {len(remaining_questions)}")

    # 9. Print label stats
    if config['print_stats_labels']:
        print("\n--- Label Statistics ---")
        label_counts_actual = {}
        label_counts_actual_per_file = [{} for _ in range(num_out_files)]
        for file_index, file_questions in enumerate(questions_in_files):
            for q in file_questions:
                for label in q['labels']:
                    label_counts_actual[label] = label_counts_actual.get(label, 0) + 1
                    label_counts_actual_per_file[file_index][label] = label_counts_actual_per_file[file_index].get(label, 0) + 1

        for label, count in sorted(label_counts_actual.items(), key=lambda item: item[1], reverse=True):
            print(f"Label '{label}': {count} questions")

        if config['print_stats']:
            print("\n--- Desired Label Constraints vs. Actual ---")
            for file_index, file_label_counts in enumerate(label_counts_actual_per_file):
                print(f"\nFile {file_index + 1}:")
                for label, constraints in config['labels'].get('constraints', {}).items():
                    actual_count = file_label_counts.get(label, 0)
                    print(f"Label '{label}': Desired min={constraints.get('min', 0)}, max={constraints.get('max', 'inf')}, Actual={actual_count}")


    # 9. Print label stats
    if config['print_stats_labels']:
        print("\n--- Label Statistics ---")
        label_counts_actual = {}
        for file_index, file_questions in enumerate(questions_in_files):
            for q in file_questions:
                for label in q['labels']:
                    label_counts_actual.setdefault(label, [0] * num_out_files)[file_index] += 1

        # Print label counts per file in a pretty table ordered by total questions
        print("\n--- Label Distribution per File (Ordered by Total Questions) ---")
        table = PrettyTable()
        field_names = ["Label"] + [f"File {i+1}" for i in range(num_out_files)]
        table.field_names = field_names

        # Calculate total questions per label
        label_totals = {label: sum(counts) for label, counts in label_counts_actual.items()}

        # Sort labels by total questions in descending order
        sorted_labels = sorted(label_totals.keys(), key=lambda label: label_totals[label], reverse=True)

        for label in sorted_labels:
            counts = label_counts_actual[label]
            row = [label] + list(map(str, counts))
            table.add_row(row)

        print(table)

        if config['print_stats']:
            print("\n--- Desired Label Constraints vs. Actual ---")
            for label, constraints in config['labels'].get('constraints', {}).items():
                actual_count = sum(label_counts_actual.get(label, [0] * num_out_files))
                print(f"Label '{label}': Desired min={constraints.get('min', 0)}, max={constraints.get('max', 'inf')}, Actual={actual_count}")

def parse_questions(text, blacklist):
    """Parses questions from the input text based on the defined format."""
    questions = []
    split_questions = re.split(r'%[\r\n]+', text.strip())
    for q_text in split_questions:
        if not q_text.strip():
            continue
        parts = q_text.strip().split('\n', 1)
        if len(parts) < 2:
            continue
        label_part = parts[0].strip()
        question_answer_part = parts[1].strip()

        match = re.match(r'\$\s*([a-zA-Z0-9_, ]+)', label_part)
        if match:
            labels = [label.strip() for label in match.group(1).split(',') if label.strip() and label.strip()]
            if labels:
                question_parts = question_answer_part.split('\n')
                question_text = ""
                answers = []
                for line in question_parts:
                    if line.startswith('_'):
                        question_text = line[1:].strip()
                    elif line.startswith('*'):
                        answers.append({'text': line[1:].strip(), 'correct': True})
                    elif line.startswith('-'):
                        answers.append({'text': line[1:].strip(), 'correct': False})

                if question_text and answers:
                    questions.append({
                        'labels': labels,
                        'question': question_text,
                        'answers': answers,
                        'original_text': '\n'+label_part+'\n'+question_answer_part+'\n'+"%"
                    })
                
                    
    return questions

if __name__ == "__main__":
    config = {
        'num_in_files': 3,
        'in_folder': 'data',
        'num_out_files': 4,
        'questions_per_out': {'min': 10, 'max': 10},
        'distribution': 1,  # 0 -> don't mix, 1 -> distribute evenly, intermediate values for a degree of mixing
        'repeat': False,
        'high_distribution': True,
        'repeat_questions': False,
        'randomize_order': True,
        'print_stats': True,
        'print_stats_labels': True,
        'labels': {
            'blacklist': ['void'],
            'weights': { 'void': 1}, # Higher weight means more likely to be picked
            'constraints': {
                'void': {'min': 1, 'max': 4},
                'void2': {'min': 2, 'max': 4}
            }
        }
    }


    create_files_with_questions(config)