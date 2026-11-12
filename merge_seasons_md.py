import os
import re
from collections import defaultdict
from pathlib import Path

def parse_srt_with_timestamps(srt_text: str, interval_seconds: int = 60) -> list:
    """
    Analizza il file SRT e raggruppa il testo in paragrafi basati su intervalli temporali (es. ogni 60 secondi).
    Restituisce una lista di tuple: (timestamp_formattato, testo_del_paragrafo).
    """
    timestamp_pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2})[,.]\d{3}\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.]\d{3}')
    
    paragraphs = []
    current_slot = -1
    current_texts = []
    slot_start_time = "00:00:00"

    lines = srt_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = timestamp_pattern.match(line)
        if match:
            h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
            total_seconds = h * 3600 + m * 60 + s
            slot = total_seconds // interval_seconds
            
            time_label = f"{match.group(1)}:{match.group(2)}:00"
            
            if slot != current_slot:
                if current_texts:
                    cleaned_paragraph = " ".join(current_texts)
                    cleaned_paragraph = re.sub(r'\s+', ' ', cleaned_paragraph).strip()
                    paragraphs.append((slot_start_time, cleaned_paragraph))
                    current_texts = []
                current_slot = slot
                slot_start_time = time_label
            
            # Avanza per leggere le righe di testo del sottotitolo
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip() != '':
                text_lines.append(lines[i].strip())
                i += 1
            
            block_text = " ".join(text_lines)
            # Rimuove tag HTML e caratteri speciali/musicali isolati
            block_text = re.sub(r'<[^>]+>', '', block_text)
            block_text = re.sub(r'^[â™ª\s]+|[â™ª\s]+$', '', block_text)
            
            if block_text:
                # Evita duplicati consecutivi nello stesso blocco
                if not current_texts or current_texts[-1] != block_text:
                    current_texts.append(block_text)
        else:
            i += 1
            
    # Aggiunge l'ultimo blocco rimanente
    if current_texts:
        cleaned_paragraph = " ".join(current_texts)
        cleaned_paragraph = re.sub(r'\s+', ' ', cleaned_paragraph).strip()
        paragraphs.append((slot_start_time, cleaned_paragraph))
        
    return paragraphs

def parse_subtitle_filename(filename: str):
    """
    Estrae automaticamente il nome dello show, la stagione e l'episodio dal nome file.
    """
    patterns = [
        re.compile(r'^(.*?)\.s(\d+)e(\d+)', re.IGNORECASE),
        re.compile(r'^(.*?)[\.\-_](\d+)[xX](\d+)', re.IGNORECASE),
        re.compile(r'^(.*?)[sS](\d+)[eE](\d+)')
    ]
    
    for p in patterns:
        match = p.search(filename)
        if match:
            raw_show_name = match.group(1)
            season = int(match.group(2))
            episode = int(match.group(3))
            show_name = re.sub(r'[\.\-_]+', ' ', raw_show_name).strip().title()
            return show_name, season, episode
            
    return None, None, None

def merge_subtitles_for_notebooklm(input_dir: str):
    input_path = Path(input_dir)
    output_path = Path(input_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    shows_data = defaultdict(lambda: defaultdict(list))
    
    print(f"Scansione dei file .srt in corso nella cartella: {input_path.resolve()}...")
    
    for srt_file in input_path.glob('**/*.srt'):
        show_name, season, episode = parse_subtitle_filename(srt_file.name)
        if show_name and season is not None and episode is not None:
            shows_data[show_name][season].append((episode, srt_file))
        else:
            print(f"[Skipped] Impossibile analizzare il file: {srt_file.name}")
            
    if not shows_data:
        print("Nessun file di sottotitoli compatibile trovato.")
        return

    for show_name, seasons in shows_data.items():
        print(f"\n🎬 Show rilevato: '{show_name}'")
        file_safe_show_name = show_name.replace(" ", "_")
        
        for season, episodes in sorted(seasons.items()):
            episodes.sort(key=lambda x: x[0])
            
            season_content = [f"# {show_name} - Stagione {season:02d}\n"]
            
            for ep_num, file_path in episodes:
                print(f"  -> Elaborazione Season {season:02d}, Episode {ep_num:02d} ({file_path.name})")
                season_content.append(f"\n## Episodio {ep_num:02d}\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        raw_text = f.read()
                    
                    # Genera i paragrafi temporizzati (intervallo di 60 secondi)
                    timed_paragraphs = parse_srt_with_timestamps(raw_text, interval_seconds=60)
                    
                    for timestamp, paragraph in timed_paragraphs:
                        season_content.append(f"**[{timestamp}]** {paragraph}\n")
                        
                except Exception as e:
                    print(f"  ❌ Errore durante la lettura di {file_path.name}: {e}")
                    
            output_file = output_path / f"{file_safe_show_name}-Season_{season:02d}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(season_content))
                
            print(f"  ✔️ Generato: {output_file.name}")

if __name__ == "__main__":
    INPUT_DIRECTORY = "./media"
    merge_subtitles_for_notebooklm(INPUT_DIRECTORY)