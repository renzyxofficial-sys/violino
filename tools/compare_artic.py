import csv, sys
py = list(csv.DictReader(open(r"C:\Users\TheoH\violino\teste\python_tecnicas.csv", encoding="utf-8")))
cc = list(csv.DictReader(open(r"C:\Users\TheoH\violino\teste\nativo_tecnicas.csv", encoding="utf-8")))
print("notas:", len(py), "python /", len(cc), "C++")
diff = [(a["idx"], a["start_s"], a["technique"], b["technique"]) for a, b in zip(py, cc) if a["technique"] != b["technique"] or abs(float(a["start_s"]) - float(b["start_s"])) > 0.002]
print("diferenças:", diff if diff else "nenhuma")
