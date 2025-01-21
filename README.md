
**Legend:**

-   `$`: Followed by comma-separated labels for the question (e.g., `$ chapter1, easy`).
-   `_`: Indicates the start of a question. For multiline questions, first line starts with `__` then for the last line, which indicates the number of correct answers there is a ending '_'.
-   `*`: Denotes a correct answer.
-   `-`: Denotes a wrong answer.
-   `#`: Followed by general feedback for the question.
-   `@`: Followed by specific feedback for the preceding answer.
-   `+`: Indicates a true/false question. Use `+T` for True and `+F` for False.
-   `%`: Separates questions.
-   `=`: The equal sign inside the text of the question or answer must be escaped with `\=`.
-   `{`: The curly brace inside the text of the question or answer must be escaped with `\{`.
-   `}`: The curly brace inside the text of the question or answer must be escaped with `\}`.

## Configuration (`config`)

The script's behavior is controlled by a configuration dictionary (`config`):

-   `'num_in_files'`: Number of input files (not currently used actively).
-   `'in_folder'`: Path to the folder containing input files.
-   `'num_out_files'`: Number of desired output files.
-   `'questions_per_out'`:
    -   `'min'`: Minimum number of questions per output file.
    -   `'max'`: Maximum number of questions per output file.
-   `'distribution'`: Controls the distribution of questions based on labels:
    -   `0`: No distribution (questions are placed in order).
    -   `1`: Even distribution (attempts to balance labels across output files).
    -   Values between 0 and 1: A mix of ordered placement and distribution.
-   `'repeat'`: If `True`, questions can be repeated across multiple output files (not currently actively used).
-   `'high_distribution'`: If `True`, amplifies the distribution effect for labels with lower weights, promoting their spread across files.
-   `'repeat_questions'`: If `False`, ensures that each unique question is used only once across all output files. If `True`, questions can appear multiple times.
-   `'randomize_order'`: If `True`, shuffles the order of questions within each output file.
-   `'print_stats'`: If `True`, prints general statistics about the question distribution.
-   `'print_stats_labels'`: If `True`, prints statistics related to label distribution.
-   `'labels'`:
    -   `'blacklist'`: List of labels that should be excluded. Questions with these labels are ignored.
    -   `'weights'`: Dictionary assigning weights to labels. Higher weight means a label is more likely to be selected during distribution. Default weight is 1.
    -   `'constraints'`: Dictionary defining constraints for labels:
        -   `'min'`: Minimum number of questions for a label across all output files.
        -   `'max'`: Maximum number of questions for a label across all output files.
        -   It's also possible to specify per-file constraints by adding `'min'` and `'max'` within a label's constraints.

## Usage

1. **Place input files** in the `data` folder.
2. **Modify the `config`** dictionary in the script to adjust the desired behavior.
3. **Run the script:** `python your_script_name.py`
4. **Output:**
    -   Output files with distributed questions will be created in the `out` folder.
    -   Moodle-formatted output files will be created in the `moodle` folder.
    -   If there are leftover questions after distribution, they will be placed in `file_quiz_last_questions` within the `out` folder and a corresponding Moodle file in the `moodle` folder.
    -   Statistics about the distribution will be printed to the console if `'print_stats'` and/or `'print_stats_labels'` are set to `True`.

## Algorithm for Score Distribution

The script aims to distribute questions across output files while considering label weights, constraints, and the desired distribution factor. 


## Moodle Conversion (`to_moodle_format` function)

This function takes an input file (in the format described above) and converts it into a text file that can be imported into Moodle. It handles:

-   **Escaping Special Characters:** Escapes special characters like `=`, `{`, and `}` that have specific meanings in Moodle's format.
-   **Question and Answer Formatting:** Formats questions, correct answers, wrong answers, and feedback according to Moodle's syntax.
-   **Multiline Questions:** Correctly handles multiline questions and calculates the score based on the number of correct answers.
-   **True/False Questions:** Converts `+T` and `+F` into `TRUE` and `FALSE` in Moodle format.
-   **Error Handling:** Checks for errors in the input file format and handles them gracefully.
-   **Tags:** Supports adding tags to questions in Moodle format.

## Notes

-   The script assumes that the input files are encoded in UTF-8.
-   The script creates the `out` and `moodle` folders if they don't exist.
-   The script is designed to handle a variety of question formats, including single-line, multiline, and true/false questions.
-   The distribution algorithm is heuristic and may not always produce a perfectly balanced distribution, especially with complex constraints.
-   The Moodle conversion function is based on the documentation for Moodle's question import format.
-   The script has error handling in place to prevent crashes due to invalid input file formats, but it is still recommended to carefully check the input files for correctness.
-   The algorithm can be further optimized for performance, especially for very large numbers of questions and output files.
-   The script has been tested, but if you experience any errors, feel free to open an issue with a sample file that reproduces the error.
