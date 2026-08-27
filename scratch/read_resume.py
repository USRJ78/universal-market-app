import pypdf

reader = pypdf.PdfReader('C:/Users/USER/OneDrive/Documents/Uday_Rathore_Finance_Resume.pdf')
text = '\n'.join([page.extract_text() for page in reader.pages])

with open('scratch/resume_extracted.txt', 'w', encoding='utf-8') as f:
    f.write(text)

print("Extracted successfully!")
