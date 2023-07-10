# -*- encoding: utf-8 -*-
# @Author: SWHL
# @Contact: liekkaskono@163.com
import argparse
import copy
import time
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

from .table_matcher import TableMatch
from .table_structure import TableStructurer
from .utils import LoadImage, vis_table

root_dir = Path(__file__).resolve().parent

DEFAULT_OCR = RapidOCR()


class RapidTable:
    def __init__(
        self, model_path: Optional[str] = None, ocr_instance: Optional[object] = None
    ):
        self.ocr_sys = DEFAULT_OCR
        if ocr_instance:
            self.ocr_sys = ocr_instance

        if model_path is None:
            model_path = str(
                root_dir / "models" / "en_ppstructure_mobile_v2_SLANet.onnx"
            )

        self.table_structure = TableStructurer(model_path)
        self.table_matcher = TableMatch()

        self.load_img = LoadImage()

    def __call__(self, img_content: Union[str, np.ndarray, bytes, Path]):
        img = self.load_img(img_content)

        s = time.time()
        dt_boxes, rec_res = self._ocr(copy.deepcopy(img))

        structure_res, _ = self.table_structure(copy.deepcopy(img))
        pred_html = self.table_matcher(structure_res, dt_boxes, rec_res)

        elapse = time.time() - s
        return pred_html, elapse

    def _ocr(self, img):
        h, w = img.shape[:2]

        ocr_result, _ = self.ocr_sys(img)
        dt_boxes, rec_res, scores = list(zip(*ocr_result))
        rec_res = list(zip(rec_res, scores))

        r_boxes = []
        for box in dt_boxes:
            box = np.array(box)
            x_min = max(0, box[:, 0].min() - 1)
            x_max = min(w, box[:, 0].max() + 1)
            y_min = max(0, box[:, 1].min() - 1)
            y_max = min(h, box[:, 1].max() + 1)
            box = [x_min, y_min, x_max, y_max]
            r_boxes.append(box)
        dt_boxes = np.array(r_boxes)
        return dt_boxes, rec_res


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--vis",
        action="store_true",
        help="Wheter to visualize the layout results.",
    )
    parser.add_argument(
        "-img", "--img_path", type=str, required=True, help="Path to image for layout."
    )
    parser.add_argument(
        "-m",
        "--model_path",
        type=str,
        default=str(root_dir / "models" / "en_ppstructure_mobile_v2_SLANet.onnx"),
        help="The model path used for inference.",
    )
    args = parser.parse_args()

    rapid_table = RapidTable(args.model_path)

    img = cv2.imread(args.img_path)
    table_html_str, elapse = rapid_table(img)
    print(table_html_str)

    if args.vis:
        img_path = Path(args.img_path)
        save_path = img_path.resolve().parent / f"vis_{img_path.stem}.html"
        vis_table(table_html_str, str(save_path))


if __name__ == "__main__":
    main()
