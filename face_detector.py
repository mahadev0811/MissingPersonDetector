from json import loads, dumps
from deepface import DeepFace
import pandas as pd
import cv2
from os.path import basename, splitext, isdir, isfile
from os import makedirs, remove
from shutil import rmtree
from traceback import format_exc
from argparse import ArgumentParser
import sqlite3
from datetime import datetime

found_dir = 'found'
with sqlite3.connect("./Database/data.db") as db:
    db.row_factory = sqlite3.Row
    cur = db.cursor()

def run_deepface(frame):
    try: 
        dfs = DeepFace.find(frame, db_path=db_path, model_name=model_name, detector_backend=detector_backend, silent=True, threshold=0.09)
        if len(dfs) > 0 and isinstance(dfs[0], pd.DataFrame) and not dfs[0].empty:
            return dfs
    except Exception as e:
        if 'Face could not be detected' in str(e):
            print('Face could not be detected')
            return None
        print(f"Error: {e}")
    return None

def sync_with_db(scan_info):
    fetch = cur.execute("SELECT * FROM missing_people where status > 1").fetchall()     # status 3 means verification failed so the search should continue for this person
    for record in fetch:
        if record['status'] == 2:
            if isdir(record['image_f']):
                rmtree(record['image_f'])
            elif isfile(record['image_f']):
                remove(record['image_f'])
        if str(record['id']) in scan_info['for_verification_pids']:
            scan_info['for_verification_pids'].pop(str(record['id']))
            with open('scan_info.json', 'w') as f:
                f.write(dumps(scan_info))
    
    return scan_info

def analyze_faces(df, frame, scan_info, surity, detected_faces_dict, src_prefix):
    src_prefix = basename(src_prefix).split('.')[0] if src_prefix is not None else '0'
    for index, row in df.iterrows():
        x, y, w, h = row['source_x'], row['source_y'], row['source_w'], row['source_h']
        person_id = splitext(basename(row['identity']))[0]

        if person_id in detected_faces_dict:
            detected_faces_dict[person_id] += 1
        else:
            detected_faces_dict[person_id] = 1

        if detected_faces_dict[person_id] == surity:
            print(f"{person_id} found with distance {row['distance']}")
            scan_info = sync_with_db(scan_info)
            detected_faces_dict.pop(person_id)
            dt = datetime.now().strftime("%Y%m%dT%H%M%S")
            if person_id in scan_info['for_verification_pids']:
                dts = [datetime.strptime(basename(f).split('.')[0], "%Y%m%dT%H%M%S") for f in scan_info['for_verification_pids'][person_id]]
                if (datetime.strptime(dt, "%Y%m%dT%H%M%S") - max(dts)).seconds >= frame_time_gap:
                    scan_info['for_verification_pids'][person_id].append(f"{found_dir}/{person_id}/{src_prefix}/{dt}.jpg")
                else:
                    continue
            else:
                scan_info['for_verification_pids'][person_id] = [f"{found_dir}/{person_id}/{src_prefix}/{dt}.jpg"]

            # annotate the frame
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            makedirs(f'{found_dir}/{person_id}/{src_prefix}', exist_ok=True)
            cv2.imwrite(f'{found_dir}/{person_id}/{src_prefix}/{dt}.jpg', frame[y-5:y+h+5, x-5:x+w+5])

    return detected_faces_dict, scan_info

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--cam_id', '-cid', type=int, default=0, help='Camera id')
    parser.add_argument('--footage_path', '-fp', type=str, default=None, help='Path to the footage')
    parser.add_argument('--db_path', '-dp', type=str, default='data', help='Path to the database')
    parser.add_argument('--model_name', '-mn', type=str, default='Dlib', choices=['VGG-Face', 'Facenet', 'OpenFace', 'DeepFace', 'DeepID', 'Dlib'], help='Model name')
    parser.add_argument('--detector_backend', '-db', type=str, default='ssd', choices=['opencv', 'ssd', 'mtcnn', 'retinaface'], help='Detector backend')
    parser.add_argument('--surity', '-s', type=int, default=2, choices=[1, 2, 3], help='Surity level')
    parser.add_argument('--frame_time_gap', '-ftg', type=int, default=10, help='Time gap between 2 face detected frames in seconds')
    args = parser.parse_args()

    cam_id, footage_path, db_path, model_name, detector_backend = args.cam_id, args.footage_path, args.db_path, args.model_name, args.detector_backend
    surity, frame_time_gap = args.surity, args.frame_time_gap

    try:    
        i, detected_faces_dict = 1, {}

        makedirs(found_dir, exist_ok=True)
        scan_info = loads(open(f'scan_info.json').read())
        cap = cv2.VideoCapture(cam_id) if footage_path is None else cv2.VideoCapture(footage_path)

        scan_info = sync_with_db(scan_info)
        scan_info['error'] = ""

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if i > surity:
                i = 1
                continue

            dfs = run_deepface(frame)
            if dfs is None:
                i += 1
                continue

            detected_faces_dict, scan_info = analyze_faces(dfs[0], frame, scan_info, surity, detected_faces_dict, footage_path)
            with open('scan_info.json', 'w') as f:
                f.write(dumps(scan_info))

            i += 1
    except Exception as e:
        scan_info['error'] = format_exc()
    finally:
        if 'cap' in locals() and cap is not None:
            cap.release()
        with open('scan_info.json', 'w') as f:
            f.write(dumps(sync_with_db(scan_info)))