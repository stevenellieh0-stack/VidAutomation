import os
import io
import json
import subprocess
import asyncio
import requests
import cv2
import numpy as np
import edge_tts
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# ==========================================
# 1. CONFIGURATION & DRIVE SETUP
# ==========================================
FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "1nIMpMl1KFMbJl_GA56tU3pFWfYQmT2AM")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
SERVICE_ACCOUNT_JSON = os.environ.get("GDRIVE_CREDENTIALS", "")

def get_drive_service():
    """Authenticates with Google Drive using a Service Account."""
    if not SERVICE_ACCOUNT_JSON:
        print("[!] No GDRIVE_CREDENTIALS secret provided.")
        return None
    creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

# ==========================================
# 2. VOICE ENGINE
# ==========================================
def generate_voice(text: str, output_path: str = "voice.mp3") -> str:
    """Generates the weathered old-man narrator voice."""
    if ELEVENLABS_KEY:
        try:
            url = "https://api.elevenlabs.io/v1/text-to-speech/ErXwobaYiN019PkySvjV" # Arthur (Vintage Storyteller)
            headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.35, "similarity_boost": 0.85}
            }
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(res.content)
                print("  [✓] Audio generated via ElevenLabs (Arthur).")
                return output_path
        except Exception as e:
            print(f"  [!] ElevenLabs failed, using Neural fallback: {e}")

    # Free Neural Engine: Christopher pitched down -15Hz for authentic elderly rasp
    print("  [>] Generating weathered storyteller voice via Neural Voice Engine...")
    async def run_tts():
        comm = edge_tts.Communicate(text, voice="en-US-ChristopherNeural", rate="-12%", pitch="-15Hz")
        await comm.save(output_path)
    asyncio.run(run_tts())
    print("  [✓] Audio generated via Neural Engine.")
    return output_path

# ==========================================
# 3. VIDEO RENDER ENGINE
# ==========================================
def render_video(scenes: list, audio_path: str, output_path: str = "final.mp4") -> str:
    """Renders dark-noir stickman animation and HUD telemetry."""
    print("  [>] Rendering video frames...")
    dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
    dur = float(subprocess.check_output(dur_cmd).decode("utf-8").strip())

    fps, width, height = 30, 1280, 720
    total_frames = int(dur * fps)

    temp_video = "temp_visuals.mp4"
    out = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    for f in range(total_frames):
        t = f / fps
        scene_idx = min(int(t / (dur / len(scenes))), len(scenes) - 1)
        scene = scenes[scene_idx]

        # Dark charcoal noir background
        frame = np.full((height, width, 3), (12, 14, 16), dtype=np.uint8)

        # Surveillance Grid
        cv2.line(frame, (60, 60), (width - 60, 60), (35, 40, 45), 1)
        cv2.line(frame, (60, height - 60), (width - 60, height - 60), (35, 40, 45), 1)

        # Walking stickman kinematics
        walk = np.sin(f * 0.1)
        cx = width // 2 + int(np.cos(f * 0.04) * 40)
        cy = height // 2 + 40 + int(np.abs(walk) * 8)
        color = (230, 240, 0) # Cyan in BGR

        # Character silhouette
        cv2.circle(frame, (cx, cy - 110), 36, color, 3)
        cv2.line(frame, (cx, cy - 74), (cx, cy + 70), color, 3)
        arm_swing = int(walk * 30)
        cv2.line(frame, (cx, cy - 35), (cx - 50, cy + arm_swing), color, 3)
        cv2.line(frame, (cx, cy - 35), (cx + 50, cy - arm_swing), color, 3)
        cv2.line(frame, (cx, cy + 70), (cx - 35 - arm_swing, cy + 180), color, 3)
        cv2.line(frame, (cx, cy + 70), (cx + 35 + arm_swing, cy + 180), color, 3)

        # Floating HUD Telemetry
        title = f"[ {scene.get('hud_title', 'TARGET ACQUIRED')} ]"
        stat = scene.get('hud_stat', 'PROBABILITY: 99.4%')
        cv2.putText(frame, title, (90, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 240, 255), 2)
        cv2.putText(frame, stat, (90, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 180, 255), 2)

        # Scanline
        scan_y = int((f * 12) % height)
        cv2.line(frame, (0, scan_y), (width, scan_y), (30, 85, 45), 2)

        out.write(frame)

    out.release()

    # Mux with FFmpeg and sub-bass tension drone
    print("  [>] Mixing audio and exporting MP4...")
    cmd = (
        f"ffmpeg -y -i {temp_video} -i {audio_path} "
        f"-f lavfi -i sine=frequency=52:duration={dur} "
        f"-filter_complex '[1:a]volume=1.4[a1];[2:a]volume=0.22[a2];[a1][a2]amix=inputs=2:duration=first' "
        f"-c:v libx264 -pix_fmt yuv420p -c:a aac -shortest {output_path}"
    )
    subprocess.run(cmd, shell=True, check=True)
    return output_path

# ==========================================
# 4. MASTER DRIVE PIPELINE EXECUTION
# ==========================================
def main():
    service = get_drive_service()
    if not service:
        print("[!] Cannot connect to Drive without credentials.")
        return

    print(f"[*] Scanning Drive folder ID: {FOLDER_ID} for new jobs...")
    query = f"'{FOLDER_ID}' in parents and name contains 'job_' and name contains '.json' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if not files:
        print("[✓] No pending jobs in queue. Drive is clean.")
        return

    for f in files:
        file_id = f['id']
        file_name = f['name']
        print(f"\n[★] Found pending job: {file_name}")

        # Download Job JSON
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        job_data = json.loads(fh.read().decode('utf-8'))

        # 1. Voice
        script_text = job_data.get("full_voiceover_script", "")
        voice_file = generate_voice(script_text)

        # 2. Render
        clean_title = job_data.get("title", "Video").replace(" ", "_").replace("?", "").replace("'", "")
        output_mp4 = f"{clean_title}.mp4"
        render_video(job_data.get("scenes", []), voice_file, output_mp4)

        # 3. Upload Finished MP4 back to Drive
        print(f"  [>] Uploading {output_mp4} to Google Drive...")
        file_metadata = {
            'name': output_mp4,
            'parents': [FOLDER_ID]
        }
        media = MediaFileUpload(output_mp4, mimetype='video/mp4', resumable=True)
        uploaded = service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
        print(f"  [🎉] SUCCESS! Video uploaded to Drive with ID: {uploaded.get('id')}")

        # 4. Rename Job File so it doesn't re-run
        service.files().update(fileId=file_id, body={'name': f"PROCESSED_{file_name}"}).execute()

        # Clean temporary local files
        for temp in [voice_file, output_mp4, "temp_visuals.mp4"]:
            if os.path.exists(temp): os.remove(temp)

if __name__ == "__main__":
    main()
