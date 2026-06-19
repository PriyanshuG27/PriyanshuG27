import urllib.request
import json
import re
import os

username = "PriyanshuG27"

def get_github_stats():
    print(f"Querying GitHub API for {username}...")
    
    # 1. Fetch repos and stars
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"
    req = urllib.request.Request(repos_url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req) as r:
            repos = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print("Error fetching repos:", e)
        return None

    total_repos = len(repos)
    total_stars = sum(repo.get('stargazers_count', 0) for repo in repos)
    
    # Calculate language percentages
    languages = {}
    for repo in repos:
        lang = repo.get('language')
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
            
    total_lang_repos = sum(languages.values())
    lang_weights = {k: round((v / total_lang_repos) * 100) for k, v in languages.items()}
    sorted_langs = sorted(lang_weights.items(), key=lambda x: x[1], reverse=True)
    
    # Ensure we have at least 5 languages for the dashboard rows
    while len(sorted_langs) < 5:
        sorted_langs.append(("N/A", 0))
        
    # 2. Fetch streak stats
    streak_url = f"https://github-readme-streak-stats.herokuapp.com/?user={username}"
    req_streak = urllib.request.Request(streak_url, headers={'User-Agent': 'Mozilla/5.0'})
    
    total_contributions = "0"
    current_streak = "0"
    longest_streak = "0"
    
    try:
        with urllib.request.urlopen(req_streak) as r:
            svg = r.read().decode('utf-8')
        
        text_contents = re.findall(r'<text[^>]*>(.*?)</text>', svg, re.DOTALL)
        if len(text_contents) >= 7:
            total_contributions = text_contents[0].strip()
            current_streak = text_contents[5].strip()
            longest_streak = text_contents[6].strip()
    except Exception as e:
        print("Error fetching streak stats:", e)

    return {
        "repos": total_repos,
        "stars": total_stars,
        "contributions": total_contributions,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "languages": sorted_langs[:5]
    }

def update_svgs(stats):
    if not stats:
        print("No stats fetched. Aborting SVG update.")
        return
        
    # Paths (relative to the repo root where the script runs in CI)
    # If run locally, it will update in the same folder
    telemetry_path = "telemetry_dashboard.svg"
    header_path = "header.svg"
    
    if not os.path.exists(telemetry_path) or not os.path.exists(header_path):
        print("SVG assets not found in the current directory. Checking parent...")
        telemetry_path = os.path.join("..", telemetry_path)
        header_path = os.path.join("..", header_path)
        
    if not os.path.exists(telemetry_path) or not os.path.exists(header_path):
        # In CI, the files should be in the root directory
        telemetry_path = os.path.join(os.getcwd(), "telemetry_dashboard.svg")
        header_path = os.path.join(os.getcwd(), "header.svg")

    if not os.path.exists(telemetry_path):
        print(f"Error: {telemetry_path} does not exist.")
        return

    # 1. Update telemetry_dashboard.svg
    print(f"Updating {telemetry_path}...")
    with open(telemetry_path, "r", encoding="utf-8") as f:
        svg_content = f.read()
        
    # Replace metrics summary
    svg_content = re.sub(
        r"COMMITS\s*:\s*<tspan[^>]*>[^<]+</tspan>",
        f"COMMITS : <tspan fill=\"#e2e8f0\" font-weight=\"bold\">{stats['contributions']}</tspan>",
        svg_content
    )
    svg_content = re.sub(
        r"STARS\s*:\s*<tspan[^>]*>[^<]+</tspan>",
        f"STARS : <tspan fill=\"#e2e8f0\" font-weight=\"bold\">{stats['stars']}</tspan>",
        svg_content
    )
    svg_content = re.sub(
        r"REPOS\s*:\s*<tspan[^>]*>[^<]+</tspan>",
        f"REPOS   : <tspan fill=\"#e2e8f0\" font-weight=\"bold\">{stats['repos']}</tspan>",
        svg_content
    )
    svg_content = re.sub(
        r"STREAK\s*:\s*<tspan[^>]*>[^<]+</tspan>",
        f"STREAK: <tspan fill=\"#f59e0b\" font-weight=\"bold\">{stats['current_streak']} Days</tspan>",
        svg_content
    )
    
    # Update Uptime Streak progress bar width (max 330)
    current = int(stats['current_streak'])
    longest = max(1, int(stats['longest_streak']))
    bar_width = int((current / longest) * 330) if longest > 0 else 0
    bar_width = max(10, min(330, bar_width)) # keep a tiny width even at 0
    
    svg_content = re.sub(
        r'<rect x="35" y="205" width="\d+" height="15" rx="3" fill="url\(#emerald-grad\)"',
        f'<rect x="35" y="205" width="{bar_width}" height="15" rx="3" fill="url(#emerald-grad)"',
        svg_content
    )
    
    # Update language list (Top 5)
    langs = stats['languages']
    # We will replace each language row text and bar width in the SVG
    colors = ["cyan-grad", "blue-grad", "amber-grad", "emerald-grad", "64748b"]
    
    # Match the language texts like "JS (42%)", "TS (28%)", etc.
    # We can replace them row-by-row
    svg_lines = svg_content.split('\n')
    
    for idx, (lang_name, lang_pct) in enumerate(langs):
        # Calculate bar width (max width 230)
        width = int(230 * (lang_pct / 100))
        width = max(2, width) if lang_pct > 0 else 0
        
        if idx == 0:
            svg_content = re.sub(r'fill="#e2e8f0" font-family="monospace" font-size="11">.*?\(.*?\)</text>', f'fill="#e2e8f0" font-family="monospace" font-size="11">{lang_name} ({lang_pct}%)</text>', svg_content, count=1)
            svg_content = re.sub(r'width="\d+" height="10" rx="2" fill="url\(#cyan-grad\)"', f'width="{width}" height="10" rx="2" fill="url(#cyan-grad)"', svg_content, count=1)
            
    # Let's use simple string replacements based on placeholders or template structure
    svg_content = svg_content.replace("JS (42%)", f"{langs[0][0]} ({langs[0][1]}%)")
    svg_content = svg_content.replace('width="97" height="10" rx="2" fill="url(#cyan-grad)"', f'width="{int(230 * (langs[0][1]/100))}" height="10" rx="2" fill="url(#cyan-grad)"')
    
    svg_content = svg_content.replace("TS (28%)", f"{langs[1][0]} ({langs[1][1]}%)")
    svg_content = svg_content.replace('width="64" height="10" rx="2" fill="url(#blue-grad)"', f'width="{int(230 * (langs[1][1]/100))}" height="10" rx="2" fill="url(#blue-grad)"')
    
    svg_content = svg_content.replace("C++ (18%)", f"{langs[2][0]} ({langs[2][1]}%)")
    svg_content = svg_content.replace('width="41" height="10" rx="2" fill="url(#amber-grad)"', f'width="{int(230 * (langs[2][1]/100))}" height="10" rx="2" fill="url(#amber-grad)"')
    
    svg_content = svg_content.replace("PY (10%)", f"{langs[3][0]} ({langs[3][1]}%)")
    svg_content = svg_content.replace('width="23" height="10" rx="2" fill="url(#emerald-grad)"', f'width="{int(230 * (langs[3][1]/100))}" height="10" rx="2" fill="url(#emerald-grad)"')
    
    svg_content = svg_content.replace("KT (2%)", f"{langs[4][0]} ({langs[4][1]}%)")
    svg_content = svg_content.replace('width="5" height="10" rx="2" fill="#64748b"', f'width="{int(230 * (langs[4][1]/100))}" height="10" rx="2" fill="#64748b"')

    with open(telemetry_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("Telemetry dashboard updated successfully!")

    # 2. Update header.svg
    print(f"Updating {header_path}...")
    with open(header_path, "r", encoding="utf-8") as f:
        header_content = f.read()
        
    # Update load factor or compiling percent dynamically or based on real metrics
    header_content = re.sub(
        r"LOAD:\s*<tspan[^>]*>[^<]+</tspan>",
        f"LOAD: <tspan fill=\"#f59e0b\">0.{stats['repos']}</tspan>",
        header_content
    )
    header_content = re.sub(
        r"COMPILING:\s*<tspan[^>]*>[^<]+</tspan>",
        f"COMPILING: <tspan fill=\"#ef4444\">{stats['current_streak']}d</tspan>",
        header_content
    )
    
    with open(header_path, "w", encoding="utf-8") as f:
        f.write(header_content)
    print("Header banner updated successfully!")

if __name__ == "__main__":
    stats = get_github_stats()
    if stats:
        print("Fetched Stats:", stats)
        update_svgs(stats)
