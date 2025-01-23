import random
import re
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_quiz_pdf(input_file_path, output_file_path):
    """
    Creates a beautiful PDF of quizzes from a text file.

    Args:
        input_file_path (str): The path to the input text file containing the questions.
        output_file_path (str): The path to the output PDF file.
    """

    doc = SimpleDocTemplate(output_file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.darkblue,
        alignment=1,  # Center
        spaceAfter=12,
    )

    question_style = ParagraphStyle(
        'QuestionStyle',
        parent=styles['BodyText'],
        fontSize=12,
        leading=14,
        spaceAfter=6,
    )

    answer_style = ParagraphStyle(
        'AnswerStyle',
        parent=styles['BodyText'],
        fontSize=12,
        leading=14,
        textColor=colors.darkgreen,
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.darkred,
    )
    

    
    story.append(Paragraph("Generated Quizzes", title_style))
    story.append(Spacer(1, 0.5 * inch))

    with open(input_file_path, "r", encoding="utf-8") as file:
        text = file.read()

    questions = parse_questions_pdf(text)

    for i, q in enumerate(questions):
        story.append(Paragraph(f"<b>Question {i+1}</b>: {q['question']}", question_style))
        story.append(Paragraph("Labels:" + ", ".join(q['labels']), label_style))

        for j, answer in enumerate(q['answers']):
            if answer['correct']:
                story.append(Paragraph(f"  - {answer['text']} (Correct)", answer_style))
            else:
                story.append(Paragraph(f"  - {answer['text']}", styles['BodyText']))

        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)

def parse_questions_pdf(text):
    """
    Parses questions from the input text based on the defined format.

    Args:
        text (str): The raw input text containing questions.

    Returns:
        list: A list of dictionaries, where each dictionary represents a question
    """

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

def create_files_with_questions(config):
    """
    Creates output files with distributed questions based on the configuration.

    Distributes questions into multiple output files based on the given configuration.
    It:
        1. Reads and concatenates question files from a designated input folder.
        2. Parses the questions, applying blacklist filters.
        3. Distributes questions among output files, respecting label weights, constraints,
        and a requested degree of distribution.
        4. Writes both raw text files and corresponding PDF quiz files.
        5. Provides tracking stats about distribution, labels, etc., if requested.

    Args:
        config (dict): A dictionary containing configuration parameters.
    """

    out_folder = "out"
    pdf_folder = "pdf"
    os.makedirs(out_folder, exist_ok=True)
    os.makedirs(pdf_folder, exist_ok=True)

    all_questions_text = ""
    for filename in os.listdir(config['in_folder']):
        in_filename = os.path.join(config['in_folder'], filename)
        if os.path.isfile(in_filename):
            try:
                with open(in_filename, 'r', encoding='utf-8') as f:
                    all_questions_text += f.read()
            except FileNotFoundError:
                print(f"Warning: Input file '{in_filename}' not found.")

    questions = parse_questions_pdf(all_questions_text)

    if not questions:
        print("No valid questions found in input files.")
        return

    weighted_labels = []
    available_questions = []
    for q in questions:
        valid_labels = [label for label in q['labels']]
        if valid_labels:
            q['labels'] = valid_labels
        available_questions.append(q)
        for label in valid_labels:
            weight = config['labels']['weights'].get(label, 1)
            weighted_labels.extend([label] * weight)

    for banned in config['labels']['blacklist']:
        for q in available_questions:
            if banned in q['labels']:
                available_questions.remove(q)

    if not available_questions:
        print("No questions available after filtering by blacklist.")
        return

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

    def can_add_question(question, file_index):
        """Checks if adding a question to a file would violate any label constraints."""
        for label in question['labels']:
            if label in label_counts_desired:
                if label_counts_desired[label]['count'] + 1 > label_counts_desired[label]['max']:
                    return False
        return True

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

                can_add_global = True
                for label in question['labels']:
                    constraints = config['labels']['constraints'].get(label, {'min': 0, 'max': float('inf')})
                    if label_counts_desired.get(label, {'count': 0})['count'] + 1 > constraints['max']:
                        can_add_global = False
                        break
                if not can_add_global:
                    continue

                can_add_file = True
                for label in question['labels']:
                    label_constraints_file = config['labels']['constraints'].get(label, {'min': 0, 'max': float('inf')})
                    if label_counts_per_file[file_index].get(label, 0) + 1 > label_constraints_file['max']:
                        can_add_file = False
                        break
                if not can_add_file:
                    continue

                score = 0.5

                for label in question['labels']:
                    score += config['labels']['weights'].get(label, 1)

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

    remaining_questions.extend(available_questions)

    for i in range(num_out_files):
        while len(questions_in_files[i]) < min_questions_per_file and remaining_questions:
            questions_in_files[i].append(remaining_questions.pop())

    if remaining_questions:
        with open(os.path.join(out_folder, "file_quiz_last_questions.txt"), 'w', encoding='utf-8') as f_last:
            for q in remaining_questions:
                f_last.write(q['original_text'] + "\n")
        create_quiz_pdf(os.path.join(out_folder, "file_quiz_last_questions.txt"), os.path.join(pdf_folder, "quiz_last_questions.pdf"))

    for i in range(num_out_files):
        out_filename = os.path.join(out_folder, "file_quiz_"+str(i + 1)+".txt")
        if randomize_order:
            random.shuffle(questions_in_files[i])
        with open(out_filename, 'w', encoding='utf-8') as f_out:
            for question in questions_in_files[i]:
                f_out.write(question['original_text'] + "\n")
        try:
            create_quiz_pdf(out_filename, os.path.join(pdf_folder, "quiz_"+str(i + 1)+".pdf"))
        except Exception as e:
            print(f"Error converting to PDF format:{str(i + 1)} , {e} ")

    if config['print_stats']:
        print("\n--- General Statistics ---")
        print(f"Total questions processed: {len(questions)}")
        print(f"Number of output files created: {num_out_files}")
        for i in range(num_out_files):
            print(f"File '{i + 1}': {len(questions_in_files[i])} questions")
        if remaining_questions:
            print(f"Questions in 'last_questions': {len(remaining_questions)}")

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

    if config['print_stats_labels']:
        print("\n--- Label Statistics ---")
        label_counts_actual = {}
        for file_index, file_questions in enumerate(questions_in_files):
            for q in file_questions:
                for label in q['labels']:
                    label_counts_actual.setdefault(label, [0] * num_out_files)[file_index] += 1

        from prettytable import PrettyTable
        print("\n--- Label Distribution per File (Ordered by Total Questions) ---")
        table = PrettyTable()
        field_names = ["Label"] + [f"File {i+1}" for i in range(num_out_files)]
        table.field_names = field_names

        label_totals = {label: sum(counts) for label, counts in label_counts_actual.items()}

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

if __name__ == "__main__":
    
    config = {
        'num_in_files': 1,
        'in_folder': 'data',
        'num_out_files': 8,
        'questions_per_out': {'min': 9, 'max': 11},
        'distribution': 1,
        'repeat': False,
        'high_distribution': True,
        'repeat_questions': False,
        'randomize_order': True,
        'print_stats': True,
        'print_stats_labels': True,
        'labels': {
            'blacklist': ['void'],
            'weights': { 'void': 1},
            'constraints': {
                'void': {'min': 1, 'max': 4},
                'void2': {'min': 2, 'max': 4}
            }
        }
    }

    create_files_with_questions(config)