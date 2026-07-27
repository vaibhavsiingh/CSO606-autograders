import pandas as pd
import ast

def process_match(s):
    try:
        val = ast.literal_eval(s)
        if isinstance(val, list):
            if len(val) > 3:
                return f"[{repr(val[0])}, {repr(val[1])}, ... ({len(val)} items)]"
        elif isinstance(val, dict):
            if len(val) > 3:
                keys = list(val.keys())[:2]
                return f"{{{repr(keys[0])}: {repr(val[keys[0]])}, {repr(keys[1])}: {repr(val[keys[1]])}, ... ({len(val)} items)}}"
    except (ValueError, SyntaxError):
        pass
    return s

def shorten_bracketed(text):
    res = ""
    i = 0
    while i < len(text):
        if text[i] in '[{':
            close_char = ']' if text[i] == '[' else '}'
            j = i + 1
            depth = 1
            while j < len(text):
                if text[j] == text[i]:
                    depth += 1
                elif text[j] == close_char:
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < len(text) and depth == 0:
                substr = text[i:j+1]
                shortened = process_match(substr)
                if shortened != substr:
                    res += shortened
                else:
                    if len(substr) > 60:
                        res += substr[:50] + f"... ({len(substr.split(','))} items approx)" + close_char
                    else:
                        res += substr
                i = j + 1
                continue
        res += text[i]
        i += 1
    return res

def process_remark(remark):
    if pd.isna(remark) or str(remark).strip() == "":
        return ""
    
    parts = [p.strip() for p in str(remark).split('|')]
    seen = set()
    cleaned_parts = []
    
    for p in parts:
        if p == "": continue
        shortened = shorten_bracketed(p)
        if shortened not in seen:
            seen.add(shortened)
            cleaned_parts.append(shortened)
            
    return " | ".join(cleaned_parts)

df1 = pd.read_csv('grade-download.csv')
df2 = pd.read_csv('grade-organise.csv')
df3 = pd.read_csv('grade-evaluate.csv')

df1 = df1.rename(columns={"marks": "marks_download", "remarks": "remarks_download"})
df2 = df2.rename(columns={"marks": "marks_organise", "remarks": "remarks_organise"})
df3 = df3.rename(columns={"marks": "marks_evaluate", "remarks": "remarks_evaluate"})

df = (
    df1[["id", "marks_download", "remarks_download"]]
    .merge(df2[["id", "marks_organise", "remarks_organise"]], on="id")
    .merge(df3[["id", "marks_evaluate", "remarks_evaluate"]], on="id")
)

df['total'] = (df['marks_download'] + df['marks_organise'] + df['marks_evaluate']).round(2)

def combine_remarks(row):
    r1 = process_remark(row['remarks_download'])
    r2 = process_remark(row['remarks_organise'])
    r3 = process_remark(row['remarks_evaluate'])
    combined = " | ".join(filter(None, [r1, r2, r3]))
    # Apply uniqueness again globally
    if combined:
        return process_remark(combined)
    return ""

df['remarks'] = df.apply(combine_remarks, axis=1)

df[['id', 'total', 'remarks']].to_csv('total.csv', index=False)
