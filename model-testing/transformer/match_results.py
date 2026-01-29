import os
import json
import operator
from pprint import pprint

def read_json_file(path):
    with open(path, 'r', encoding="utf-8") as f:
        return json.load(f)

def link_json(output_dir, input_json_path):
    with open(input_json_path, 'r', encoding="utf-8") as f:
        input_data = json.load(f)

    # sort entities by global start index
    input_json = sorted(input_data, key=operator.itemgetter("start"))

    # get all JSON files and sort them by page number
    # get only page OCR JSON files (skip replacements.json and anything else)
    json_files = [f for f in os.listdir(output_dir) if f.endswith(".json") and "_page" in f and f.endswith("_ocr.json")]
    json_files.sort(key=lambda x: int(x.split('_page')[1].split('_')[0]))


    # load pages and compute global offsets per page using full_text length
    # sep must match how you built the global text for input_json offsets
    sep = 1  # if "\n" between them; set to 0 if none, 2 if "\n\n"
    pages = []
    global_offset = 0

    for filename in json_files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'r', encoding="utf-8") as file:
            json_page = json.load(file)

        tokens = json_page.get("tokens", [])
        page_text_len = len(json_page.get("full_text", ""))  # page-local length

        pages.append({
            "filename": filename,
            "filepath": filepath,
            "json_page": json_page,
            "tokens": tokens,
            "offset": global_offset,
        })

        global_offset += page_text_len + sep

    k = 0  # entity index

    for i, page in enumerate(pages):

        offset = page["offset"]
        tokens = page["tokens"]

        for word in tokens:
            if k >= len(input_json):
                break

            word_start = word["char_start"] + offset
            word_end = word["char_end"] + offset

            # advance k until current entity could overlap this word
            while k < len(input_json) and word_start >= input_json[k]["end"]:
                k += 1

            if k >= len(input_json):
                break

            es = input_json[k]["start"]
            ee = input_json[k]["end"]

            # overlap test: [word_start, word_end) overlaps [es, ee)
            if (word_start < ee) and (word_end > es):
                # first token that contains entity start gets replacement; rest blank
                if word_start <= es < word_end:
                    word["replacement"] = input_json[k]["replacement"]
                else:
                    word["replacement"] = ""

        # write back updated page json (overwrite the page file)
        page["json_page"]["tokens"] = tokens
        with open(page["filepath"], "w", encoding="utf-8") as f:
            json.dump(page["json_page"], f, ensure_ascii=False, indent=2)

    # all_words = [p["tokens"] for p in pages]
    # with open(f"{output_dir}/replacements.json", "w", encoding="utf-8") as f:
    #     json.dump(all_words, f, ensure_ascii=False, indent=2)

# if __name__ == "__main__":
#     output = "ocr_output/sample_pdf"
#     input_ = "logs/sample/4/results_20260122_125308"           
#     link_json(output, input_)
