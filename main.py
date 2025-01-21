import os
import random
from prettytable import PrettyTable
import re
import time




def to_moodle_format(input_file_path, output_file):
    """
    Converts a text file of questions into Moodle GIFT format. 

    It handles both single-line and multi-line questions, including correct and 
    incorrect answers, feedback (both specific and generic), and tags.

    Args:
        input_file_path (str): The path to the input text file containing the questions.
        output_file (str): The path to the output file where the Moodle GIFT formatted 
                           questions will be written.

    The input file is expected to follow a specific format:
        - Questions start with an underscore '_'.
        - Correct answers start with an asterisk '*'.
        - Incorrect answers start with a hyphen '-'.
        - Generic feedback (for the entire question) starts with '####'.
        - Specific feedback (for a particular answer) starts with '#'.
        - Tags are indicated by a line starting with '$' followed by comma-separated tags.
        - A line with a single '%' indicates the end of a question.
        - Multi-line questions are indicated by two or more underscores in the question line and the number of correct answers at the end of the question line.
        - The number of correct answers for a question is indicated by a single digit at the end of the question line.
        - True/False questions are indicated by a '+' followed by 'T' for True or 'F' for False.

    The function performs the following actions:
        1. Reads the input file line by line.
        2. Parses each line to identify questions, answers, feedback, and tags.
        3. Formats the parsed content into Moodle GIFT format.
        4. Writes the formatted content to the output file.
        5. Handles errors such as missing separators, incorrect answer formats, or missing files.
        6. Removes the output file if an error is encountered during processing.

    Example Input File Format:
        $tag1, tag2
        _What is the capital of France?1
        *Paris
        -London
        -Berlin
        ####This is a general feedback for the question.
        @This is specific feedback for the correct answer.
        @This is another specific feedback.
        %
        _What are the primary colors?_ 2
        *Red
        -Green
        *Blue
        -Orange
        %

    Example Output in Moodle GIFT Format:
        // question: 1  name: What is the capital of France?
        // [tag:tag1] [tag:tag2] 
        ::What is the capital of France?::[html]<p><strong>What is the capital of France?</strong></p>{
            =Paris #This is specific feedback for the correct answer. #This is another specific feedback.
            ~London
            ~Berlin
        ####This is a general feedback for the question.
        }

        // question: 2  name: What are the primary colors?
        ::What are the primary colors?::[html]<p><strong>What are the primary colors?</strong></p>{
            ~%50.00000%Red
            ~Green
            ~%50.00000%Blue
            ~Orange
        }

    """

    # Check if the input file exists
    if not os.path.exists(input_file_path):
        print("Error, file not found")
        return

    # Open the input and output files with UTF-8 encoding
    input_file = open(input_file_path, "r",encoding='utf8')
    output_file = open(output_file, "w",encoding='utf8')

    # Initialize variables for tracking question processing
    score = -1  # Stores the score for multiple-choice questions (calculated as 100 / number of correct answers)
    counter = 0  # Counts the number of questions processed
    line_counter = 0  # Tracks the current line number in the input file
    sep_counter = 0  # Counts the number of separators encountered
    tags = []  # Stores the tags for the current question
    inSpecificFeedback = False  # Flag to indicate if currently processing specific feedback
    inGenericFeedback = False  # Flag to indicate if currently processing generic feedback
    error = False  # Flag to indicate if an error has occurred during processing

    # Initialize variables for handling multi-line questions
    separator = True  # Flag to indicate if a separator is expected
    inside_multiline_question = False  # Flag to indicate if currently processing a multi-line question
    multiline_question_buffer = []  # Buffer to store lines of a multi-line question

    # Iterate through each line in the input file
    for line in input_file:
        line_counter += 1

        # Escape special characters '=', '{', and '}' for Moodle GIFT format
        if line.__contains__("="):
            line = line.replace("=", "\\=")
        if line.__contains__("{"):
            line = line.replace("{", "\\{")
        if line.__contains__("}"):
            line = line.replace("}", "\\}")

        # Handle multi-line questions
        if inside_multiline_question:
            if "_" in line:
                # End of multi-line question
                multiline_question_buffer.append(line.strip())
                question = "\n".join(multiline_question_buffer).replace("_","")
                inside_multiline_question = False

                # Process the complete multi-line question
                counter += 1
                if question[-1] == ':':
                    question += " "  # Add a space if the question ends with a colon

                # Check for the number of correct answers at the end of the question
                if not question[-1].isdigit():
                    print(question + ("+"))
                    print(f"Error, number of correct multiline answers missing at the line: {line_counter} in file {input_file_path}")
                    error = True
                    output_file.close()
                    os.remove(output_file.name)  # Remove the output file if an error occurred
                    break

                n_corr = int(question[-1])  # Get the number of correct answers
                question = question[:-1]  # Remove the number of correct answers from the question
                question=question.replace("\n", "<br>")  # Replace newlines with <br> for HTML formatting in Moodle

                # Calculate the score for each correct answer if there are multiple correct answers
                if n_corr > 1:
                    score = 100 / n_corr

                # Write the question header to the output file
                output_file.write(f"// question: {counter}  name: {question}\n")
                # Write tags if any
                if len(tags) > 0:
                    output_file.write("// ")
                    for tag in tags:
                        output_file.write(f"[tag:{tag}] ")
                    output_file.write("\n")
                # Write the question in Moodle GIFT format with HTML markup
                output_file.write(f"::{question}::[html]<p><strong>{question}</strong></p>{{\n")
            else:
                # Continue building the multi-line question
                multiline_question_buffer.append(line.strip())
            continue

        # Handle single-line questions and other elements
        if line[0] == '_':  # question case
            inSpecificFeedback = False
            inGenericFeedback = False
            if separator:
                separator = False
                if line.count("_") >= 2:  # Multiline question case
                    inside_multiline_question = True
                    multiline_question_buffer = [line.strip()]
                else:
                    # Single-line question
                    line = line.strip()
                    question = line[1:-1]  # Extract the question text
                    counter += 1

                    if question[-1] == ':':
                        question += " "  # Add a space if the question ends with a colon

                    # Check for the number of correct answers
                    if not line[-1].isdigit():
                        print(f"Error, number of correct answers missing at the line: {line_counter} in file {input_file_path}")
                        error = True
                        output_file.close()
                        os.remove(output_file.name)  # Remove the output file if an error occurred
                        break

                    n_corr = int(line[-1]) # Get the number of correct answers

                    # Calculate the score if there are multiple correct answers
                    if n_corr > 1:
                        score = 100 / n_corr

                    # Write the question header to the output file
                    output_file.write(f"// question: {counter}  name: {question}\n")
                    # Write tags if any
                    if len(tags) > 0:
                        output_file.write("// ")
                        for tag in tags:
                            output_file.write(f"[tag:{tag}] ")
                        output_file.write("\n")
                    # Write the question in Moodle GIFT format with HTML markup
                    output_file.write(f"::{question}::[html]<p><strong>{question}</strong></p>{{\n")

            else:
                # Missing separator between questions
                print(f"Error, missing separator before line: {line_counter}")
                error = True
                output_file.close()
                os.remove(output_file.name)  # Remove the output file if an error occurred
                break

        elif line[0] == '$':  # Tag definition
            # Extract and store tags
            tags = line[1:].strip().split(",")
            tags = list(filter(lambda t: t != "", tags))

        elif line[0] == '*':  # Correct answer
            inSpecificFeedback = False
            inGenericFeedback = False
            correct_answer = line[1:]
            # Write the correct answer with score (if applicable) in Moodle GIFT format
            if score != -1:
                output_file.write(f"\t~%{score:.5f}%[moodle]{correct_answer}")
            else:
                output_file.write(f"\t=[moodle]{correct_answer}")

        elif line[0] == '-':  # Incorrect answer
            inSpecificFeedback = False
            inGenericFeedback = False
            wrong_answer = line[1:]
            # Write the incorrect answer in Moodle GIFT format
            output_file.write(f"\t~[moodle]{wrong_answer}")

        elif line[0] == '#':  # Generic feedback
            feedback = line[1:]
            inSpecificFeedback = False
            # Write generic feedback in Moodle GIFT format
            if not inGenericFeedback:
                output_file.write(f"\t####[moodle]{feedback}")
                inGenericFeedback = True
            else:
                output_file.write(f"\t{feedback}")

        elif line[0] == '@':  # Specific feedback
            feedback = line[1:]
            inGenericFeedback = False
            # Write specific feedback in Moodle GIFT format
            if not inSpecificFeedback:
                output_file.write(f"\t#[moodle]{feedback}")
                inSpecificFeedback = True
            else:
                output_file.write(f"\t{feedback}")

        elif line[0] == '+':  # True/False question
            inSpecificFeedback = False
            inGenericFeedback = False
            answer = line[1]
            # Write True/False answer in Moodle GIFT format
            if answer == 'T':
                output_file.write(f"\tTRUE\n")
            elif answer == 'F':
                output_file.write(f"\tFALSE\n")
            else:
                print("Error, wrong answer format")
                error = True

        elif line[0] == '%':  # Question separator
            inSpecificFeedback = False
            inGenericFeedback = False
            sep_counter += 1
            # Close the current question in Moodle GIFT format
            output_file.write("}\n\n")
            separator = True
            score = -1  # Reset score

        else:
            # Invalid line format
            if len(line.strip()) > 0:
                print(f"Error: missing symbol indicator at line {line_counter}\n\t{line}")
                error = True
                output_file.close()
                os.remove(output_file.name)  # Remove the output file if an error occurred
                break

    # Check for errors after processing all lines
    if not error:
        if sep_counter != counter:
            print(f"You missed the last separator {counter} {sep_counter} {input_file}")
            output_file.close()
            os.remove(output_file.name)  # Remove the output file if an error occurred
        else:
            print(f"You just created {counter} questions")

def create_files_with_questions(config):
    """
    Creates output files with distributed questions based on the configuration.

    Distributes questions into multiple output files based on the given configuration.
    It:
        1. Reads and concatenates question files from a designated input folder.
        2. Parses the questions, applying blacklist filters.
        3. Distributes questions among output files, respecting label weights, constraints,
        and a requested degree of distribution.
        4. Writes both raw text files and corresponding Moodle GIFT files.
        5. Provides tracking stats about distribution, labels, etc., if requested.

    Args:
        config (dict): A dictionary containing configuration parameters.



    """

    out_folder = "out"
    moodle_folder = "moodle"
    os.makedirs(out_folder, exist_ok=True)  # Create the output folder if it doesn't exist
    os.makedirs(moodle_folder, exist_ok=True)  # Create the moodle output folder if it doesn't exist

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
            if banned in q['labels']:
                available_questions.remove(q)

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

    questions_in_files = [[] for _ in range(num_out_files)]  # Initialize a list to store questions for each output file
    remaining_questions = []  # Initialize a list to store questions that couldn't be distributed
    used_questions = set()  # Keep track of questions that have already been used (if repeat_questions is False)

    label_counts_desired = {} # Initialize a dictionary to store the desired minimum and maximum counts for each label
    for label, constraints in config['labels'].get('constraints', {}).items():
        label_counts_desired[label] = {'min': constraints.get('min', 0), 'max': constraints.get('max', float('inf')), 'count': 0}

    # Helper function to check if adding a question violates label constraints
    def can_add_question(question, file_index):
        """Checks if adding a question to a file would violate any label constraints."""
        for label in question['labels']:
            if label in label_counts_desired:
                if label_counts_desired[label]['count'] + 1 > label_counts_desired[label]['max']:
                    return False
        return True

    # 5. Distribute questions

    if config['randomize_order']:
        random.seed(os.urandom(4))
        random.shuffle(available_questions) # Shuffle the available questions if randomize_order is True

    # Initialize dictionaries to track label counts per file and total labels per file
    label_counts_per_file = [{} for _ in range(config['num_out_files'])]
    total_labels_per_file = [0] * config['num_out_files']

    for file_index in range(config['num_out_files']):
        # Distribute questions to each file until the maximum is reached or no more questions are available
        while len(questions_in_files[file_index]) < config['questions_per_out']['max'] and available_questions:
            possible_questions = [] # Initialize a list to store possible questions for the current file
            for q_index, question in enumerate(available_questions):
                # Skip questions that have already been used if repeat_questions is False
                if not config['repeat_questions'] and question['original_text'] in used_questions:
                    continue

                # Check global label constraints (across all files)
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

                # Apply distribution to balance labels across files
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

                # Give extra weight to less frequent labels if high_distribution is True
                if config['high_distribution']:
                    for label in question['labels']:
                        if label in config['labels']['weights'] and config['labels']['weights'][label] < 2:
                            score *= 1 + (config['high_distribution'] * 0.6)

                # Add some randomness to the score to avoid always picking the same questions
                score += random.random()*10
                if score <0:
                    score += random.random()*20

                possible_questions.append((question, score, q_index)) # Add the question, its score, and its original index to the list of possible questions

            # If there are possible questions, pick the one with the highest score
            if possible_questions:
                best_question, best_score, original_index = max(possible_questions, key=lambda item: item[1])
                questions_in_files[file_index].append(best_question)
                if not config['repeat_questions']:
                    used_questions.add(best_question['original_text'])
                # Update label counts
                for label in best_question['labels']:
                    label_counts_desired[label] = label_counts_desired.get(label, {'count': 0})
                    label_counts_desired[label]['count'] += 1
                    label_counts_per_file[file_index][label] = label_counts_per_file[file_index].get(label, 0) + 1
                total_labels_per_file[file_index] += len(best_question['labels'])
                available_questions.pop(original_index) # Remove the selected question from the available questions
            else:
                break

    remaining_questions.extend(available_questions) # Add any remaining questions to the remaining_questions list

    # 6. Ensure minimum questions per file and handle remaining
    for i in range(num_out_files):
        # If a file has fewer than the minimum number of questions, add questions from the remaining_questions list
        while len(questions_in_files[i]) < min_questions_per_file and remaining_questions:
            questions_in_files[i].append(remaining_questions.pop())

    # Any truly leftover questions go to "last_questions"
    if remaining_questions:
        # Write remaining questions to a separate file
        with open(os.path.join(out_folder, "file_quiz_last_questions"), 'w', encoding='utf-8') as f_last:
            for q in remaining_questions:
                f_last.write(q['original_text'] + "\n")
        # Convert the "last_questions" file to Moodle format
        to_moodle_format(os.path.join(out_folder, "file_quiz_last_questions"), os.path.join(moodle_folder, "moodle_file_quiz_last_questions.txt"))

    # 7. Write questions to output files
    for i in range(num_out_files):
        # Write questions for each file to a separate output file
        out_filename = os.path.join(out_folder, "file_quiz_"+str(i + 1)+".txt")
        if randomize_order:
            random.shuffle(questions_in_files[i]) # Shuffle the questions in each file if randomize_order is True
        with open(out_filename, 'w', encoding='utf-8') as f_out:
            for question in questions_in_files[i]:
                f_out.write(question['original_text'] + "\n")
        try:
            # Convert each output file to Moodle format
            to_moodle_format(out_filename, os.path.join(moodle_folder, "moodle_file_quiz_"+str(i + 1)+".txt"))
        except Exception as e:
            print(f"Error converting to moodle format:{str(i + 1)} , {e} ")

    # 8. Print stats
    if config['print_stats']:
        # Print general statistics about the question distribution
        print("\n--- General Statistics ---")
        print(f"Total questions processed: {len(questions)}")
        print(f"Number of output files created: {num_out_files}")
        for i in range(num_out_files):
            print(f"File '{i + 1}': {len(questions_in_files[i])} questions")
        if remaining_questions:
            print(f"Questions in 'last_questions': {len(remaining_questions)}")

    # 9. Print label stats
    if config['print_stats_labels']:
        # Print statistics about label distribution
        print("\n--- Label Statistics ---")
        label_counts_actual = {}
        label_counts_actual_per_file = [{} for _ in range(num_out_files)]
        # Count the actual number of questions for each label in each file
        for file_index, file_questions in enumerate(questions_in_files):
            for q in file_questions:
                for label in q['labels']:
                    label_counts_actual[label] = label_counts_actual.get(label, 0) + 1
                    label_counts_actual_per_file[file_index][label] = label_counts_actual_per_file[file_index].get(label, 0) + 1

        # Print the total number of questions for each label
        for label, count in sorted(label_counts_actual.items(), key=lambda item: item[1], reverse=True):
            print(f"Label '{label}': {count} questions")

        if config['print_stats']:
            # Print a comparison between desired and actual label counts per file
            print("\n--- Desired Label Constraints vs. Actual ---")
            for file_index, file_label_counts in enumerate(label_counts_actual_per_file):
                print(f"\nFile {file_index + 1}:")
                for label, constraints in config['labels'].get('constraints', {}).items():
                    actual_count = file_label_counts.get(label, 0)
                    print(f"Label '{label}': Desired min={constraints.get('min', 0)}, max={constraints.get('max', 'inf')}, Actual={actual_count}")

    # 9. Print label stats in a table format
    if config['print_stats_labels']:
        print("\n--- Label Statistics ---")
        label_counts_actual = {}
        # Count label occurrences across files
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

        # Add rows to the table
        for label in sorted_labels:
            counts = label_counts_actual[label]
            row = [label] + list(map(str, counts))
            table.add_row(row)

        print(table)

        if config['print_stats']:
            # Print a comparison between desired and actual label counts (total)
            print("\n--- Desired Label Constraints vs. Actual ---")
            for label, constraints in config['labels'].get('constraints', {}).items():
                actual_count = sum(label_counts_actual.get(label, [0] * num_out_files))
                print(f"Label '{label}': Desired min={constraints.get('min', 0)}, max={constraints.get('max', 'inf')}, Actual={actual_count}")

def parse_questions(text, blacklist):
    """
    Parses questions from the input text based on the defined format.

    Args:
        text (str): The raw input text containing questions.
        blacklist (list): A list of blacklisted labels to ignore.

    Returns:
        list: A list of dictionaries, where each dictionary represents a question 
              and contains the following keys:
                - 'labels': A list of labels associated with the question.
                - 'question': The question text.
                - 'answers': A list of dictionaries, where each dictionary represents an answer 
                             and contains the following keys:
                                - 'text': The answer text.
                                - 'correct': A boolean indicating whether the answer is correct.
                - 'original_text': The original raw text of the question, including labels and answers.
    """

    questions = []
    split_questions = re.split(r'%[\r\n]+', text.strip()) # Split the text into questions based on the '%' delimiter
    for q_text in split_questions:
        if not q_text.strip():
            continue
        parts = q_text.strip().split('\n', 1) # Split each question into label part and question/answer part
        if len(parts) < 2:
            continue
        label_part = parts[0].strip()
        question_answer_part = parts[1].strip()

        # Extract labels using a regular expression
        match = re.match(r'\$\s*([a-zA-Z0-9_, ]+)', label_part)
        if match:
            labels = [label.strip() for label in match.group(1).split(',') if label.strip() and label.strip()]
            if labels:
                question_parts = question_answer_part.split('\n')
                question_text = ""
                answers = []
                # Parse question and answers
                for line in question_parts:
                    if line.startswith('_'):
                        question_text = line[1:].strip() # Extract question text
                    elif line.startswith('*'):
                        answers.append({'text': line[1:].strip(), 'correct': True}) # Extract correct answer
                    elif line.startswith('-'):
                        answers.append({'text': line[1:].strip(), 'correct': False}) # Extract incorrect answer

                # Add the question to the list if it has both a question and answers
                if question_text and answers:
                    questions.append({
                        'labels': labels,
                        'question': question_text,
                        'answers': answers,
                        'original_text': '\n'+label_part+'\n'+question_answer_part+'\n'+"%" # Store the original text for later use
                    })

    return questions


"""
    The `config` dictionary should have the following structure:


    config = {
        'num_in_files': 1,  # (Deprecated - now reads all files in 'in_folder') Number of input files to process.
        'in_folder': 'data',  # The folder containing the input question files.
        'num_out_files': 8,  # The number of output files to generate.
        'questions_per_out': {'min': 9, 'max': 11},  # Minimum and maximum number of questions per output file.
        'distribution': 1,  # Distribution factor: 0 -> don't mix, 1 -> distribute evenly, intermediate values for a degree of mixing.
        'repeat': False,  # (Deprecated - now controlled by 'repeat_questions')
        'high_distribution': True, #  If True, gives more weight to less frequent labels (with weight < 2) during distribution.
        'repeat_questions': False,  # If True, allows questions to be repeated across output files.
        'randomize_order': True,  # If True, randomizes the order of questions in each output file.
        'print_stats': True,  # If True, prints general statistics about the question distribution.
        'print_stats_labels': True,  # If True, prints statistics about label distribution.
        'labels': {
            'blacklist': ['void'],  # List of labels to exclude from the distribution.
            'weights': { 'void': 1}, # Weights for each label. Higher weight means more likely to be picked.
            'constraints': {  # Minimum and maximum number of questions for each label (per file).
                'void': {'min': 1, 'max': 4},
                'void2': {'min': 2, 'max': 4}
            }
        }
    }



    In essence:

    1. Place question files in the 'data' folder.
    2. Configure this 'config' dictionary to control output file generation, distribution, label weights, and constraints.
    3. Run the script. Output files (raw text and Moodle format) will be created in the 'out' and 'moodle' folders.
    4. Review the printed statistics to verify the distribution.
    5. The moodle format files are in the moodle folder and ready for import to your Moodle platform.
    6. The txt format files are located in the out folder and could be used for generate pdf quizzes.

    Modify these config values to customize the quiz generation process to your needs.

    IMPORTANT: There can be conflicts between the constraints and the distribution factor. 


"""


if __name__ == "__main__":
    
    config = {
        'num_in_files': 1,
        'in_folder': 'data',
        'num_out_files': 8,
        'questions_per_out': {'min': 9, 'max': 11},
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