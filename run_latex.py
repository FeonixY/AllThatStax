import subprocess

def run_latex(
    latex_file_name : str,
    latex_text_name : str):

    with open(latex_text_name, "r", encoding = "utf-8") as latex_text:
        latex_text_content = latex_text.read()

    with open(latex_file_name, "r", encoding = "utf-8") as latex_file:
        latex_file_content = latex_file.readlines()

    start_idx = None
    end_idx = None
    for i, line in enumerate(latex_file_content):
        if "% Latex text starts here" in line:
            start_idx = i
        if "% Latex text ends here" in line:
            end_idx = i
            break

    if start_idx is not None and end_idx is not None:
        latex_file_content = (
            latex_file_content[:start_idx] +
            ["\n", latex_text_content, "\n"] +
            latex_file_content[end_idx:]
        )

    with open(latex_file_name, "w", encoding = "utf-8") as latex_file:
        latex_file.writelines(latex_file_content)

    command = ["xelatex.exe", "-synctex=1", "-interaction=nonstopmode", "-shell-escape", latex_file_name]

    result = subprocess.run(command, capture_output = True, text = True, encoding = "utf-8")

    print(result.stdout)
