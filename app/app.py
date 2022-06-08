from flask import Flask, render_template, jsonify
from script.laneMerge import LaneMerge
import threading

app = Flask(__name__, static_url_path='/static')

lane_merge = LaneMerge()

@app.route("/")
def home():
    # 1000ms refresh rate
    refresh_rate = 1000

    lane_merge_thread = threading.Thread(target = lane_merge.run)
    lane_merge_thread.start()

    return render_template("index.html", refresh_rate = refresh_rate, rsu_pos = lane_merge.rsu.rsu_coords,
                           obu_1_start_pos = lane_merge.OBUs[0].start_pos, obu_2_start_pos = lane_merge.OBUs[1].start_pos)

@app.route("/update_map", methods=["GET", "POST"])
def update_map():
    status = lane_merge.get_status()
    return jsonify(status)

if __name__ == "__main__":
    app.run(debug=True, threaded=True)