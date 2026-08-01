"""
==============================================================================
  FAST DUPLICATE FILE CLEANER: DOWNLOADS FOLDER
==============================================================================
"""

import os, sys

# Unbuffered line output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

def clean_duplicates():
    dl_dir = os.path.expanduser('~/OneDrive/Documents/Downloads')
    print("=" * 75)
    print("  FAST DUPLICATE FILE CLEANER — REMOVING REDUNDANT COPIES")
    print("=" * 75)

    seen = {}
    deleted_count = 0
    freed_bytes = 0

    for root, _, files in os.walk(dl_dir):
        for f in files:
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
                if sz < 100000:  # Skip tiny files (< 100 KB)
                    continue

                # Key on (filename, size)
                key = (f.lower(), sz)

                if key in seen:
                    # Duplicate found! Delete this copy, keep the original
                    orig_fp = seen[key]
                    os.remove(fp)
                    freed_bytes += sz
                    deleted_count += 1
                    print(f"  [DELETED DUPLICATE] {f[:50]:50s} | Freed: {sz / (1024*1024):.2f} MB")
                else:
                    seen[key] = fp

            except Exception as e:
                print(f"  [WARN] Skipping {f}: {e}")

    print("=" * 75)
    print(f"  CLEANUP COMPLETE: Deleted {deleted_count} duplicate files.")
    print(f"  TOTAL FREED SPACE: {freed_bytes / (1024*1024):,.2f} MB ({freed_bytes / (1024*1024*1024):.2f} GB)")
    print("=" * 75)

if __name__ == "__main__":
    clean_duplicates()
