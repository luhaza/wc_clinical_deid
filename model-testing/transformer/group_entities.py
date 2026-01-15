from Levenshtein import distance
from rapidfuzz import fuzz, process
from pprint import pprint
import itertools

strings = ["Jenny Lee", "Jenniferr   K.  Lee", "Jennifer Lee", "Jenny", "John Lee", "John Smith", "Jennifer", "Jen", "John", "Jennifer Lee MD", "Johnathan", "Luke", "Jennifer Smith"]
strings2 = ["Luke Rostan", "Luke Zanuck", "Luke Tichi", "Luke Harrison Zanuck"]
strings = [s.lower() for s in strings]
strings_split = [s.split() for s in strings]
# smallest_lvl = [s for s in strings_split if len(s) == min(len(s2) for s2 in strings_split)]
smallest_lvl = [s for s in strings_split if len(s) == min(len(s2) for s2 in strings_split)]
print(smallest_lvl)
# print(strings_split)

def get_similarity_list(strings, score_cutoff=0):
    results = {}
    for str1 in strings:
        for str2 in strings:
            if str1 != str2 and (str1, str2) not in results and (str2, str1) not in results:
                score = fuzz.WRatio(str1, str2, score_cutoff=score_cutoff)
                results[(str1, str2)] = score

    return results

# pprint(sorted(results.items(), key=lambda x: x[1], reverse=True))

buckets = {}
num_buckets = 0

def create_buckets(strings):
    buckets = {}
    placed = set()
    num_buckets = 1
    
    smallest_lvl = [s for s in strings if len(s) == min(len(s2) for s2 in strings)]
    list_1d = list(itertools.chain.from_iterable(smallest_lvl))
    small_results = get_similarity_list(list_1d, score_cutoff=75)
    sorted_results = dict(sorted(small_results.items(), key=lambda x: x[1], reverse=True))
    for result in sorted_results:
        str1, str2 = result
        score = sorted_results[result]
        if score > 0:
            bucket_found = False
            for _, bucket in buckets.items():
                if str1 in bucket or str2 in bucket:
                    bucket.add(str1)
                    bucket.add(str2)
                    placed.add(str1)
                    placed.add(str2)
                    bucket_found = True
                    break
            if not bucket_found:
                buckets[num_buckets] = set([str1, str2])
                placed.add(str1)
                placed.add(str2)
                num_buckets += 1
        else:
            if str1 not in placed:
                buckets[num_buckets] = set([str1])
                placed.add(str1)
                num_buckets += 1
            if str2 not in placed:
                buckets[num_buckets] = set([str2])
                placed.add(str2)
                num_buckets += 1
    
    return buckets, placed

def fill_buckets(buckets, placed, strings):
    # Sort buckets by ID to ensure order of reps matches bucket IDs 0..N behavior if needed
    # And sort the set content to pick a deterministic representative (e.g. longest or first alphabetical)
    bucket_reps = [sorted(list(buckets[k]))[0] for k in sorted(buckets.keys())]
    num_buckets = len(bucket_reps)
    print(bucket_reps)

    for str in strings:
        if str not in placed:
            print(str)
            result = process.extractOne(str, bucket_reps, scorer=fuzz.WRatio, score_cutoff=70)

            if result:
                _, score, bucket_idx = result
                # map list index back to bucket key (assuming keys are 1-based and sequential from create_buckets)
                # create_buckets uses 1-based keys. bucket_reps is 0-indexed.
                bucket_key = sorted(buckets.keys())[bucket_idx]
                
                buckets[bucket_key].add(str)
                placed.add(str)
            else:
                num_buckets += 1
                buckets[num_buckets] = set([str])
                placed.add(str)

    return buckets


buckets, placed = create_buckets(strings_split)
print(buckets)
# pprint(fill_buckets(buckets, strings))
print(fill_buckets(buckets, placed, strings))


# for pair, score in results.items():
#     str1, str2 = pair
#     if len(buckets) == 0:
#         num_buckets += 1
#         buckets[num_buckets] = [str1]

    # 

