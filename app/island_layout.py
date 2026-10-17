# -*- coding: utf-8 -*-
"""灵动岛布局。三条硬性规则：

1. 菜单栏下方是应用窗口的内容区，常驻显示时绝不进入（只有鼠标悬停时才临时弹出面板）。
2. 刘海两侧只用“确实测到是空的”位置；某一侧测量失败，按“有图标”处理。
3. 两侧都没有确认的空位时，岛只占刘海本身（刘海区域没有像素，黑色不可见，不遮挡任何东西），
   额度改为显示在菜单栏 ✦ 图标旁 —— 那里由系统排布，保证不和其他图标重叠。

输入都是全局横坐标（单位：点）：
  notch_l / notch_r   刘海左右边缘（没有刘海的屏幕，两者都等于屏幕中线）
  scr_l / scr_r       屏幕左右边缘
  obstacles           菜单栏上已有元素的 [(x0, x1)]：状态栏图标、应用菜单
输出 mode：
  wings   两侧都有空位：左边活动指示，右边额度
  left    只有左侧有空位：全部内容放在左侧
  right   只有右侧有空位：全部内容放在右侧
  none    两侧都没有确认的空位：只占刘海本身（没有刘海的屏幕上不显示）
"""

GAP = 8            # 与已有图标保持的距离
WING_MAX = 96      # 单侧最宽
NEED_DOT = 34      # 只放活动指示
NEED_PCT = 58      # 放下“100%”
NEED_BOTH = 96     # 一侧放下活动指示、数量和额度（实测约 92 点）
SIDES = ("auto", "left", "right")


def free_space(notch_l, notch_r, scr_l, scr_r, obstacles):
    """刘海左右两侧各有多少空余宽度（已扣除间距）。"""
    right_edge, left_edge = scr_r, scr_l
    for x0, x1 in obstacles:
        if x1 <= x0:
            continue
        if x0 < notch_r < x1:
            right_edge = min(right_edge, notch_r)
        if x0 < notch_l < x1:
            left_edge = max(left_edge, notch_l)
        if x0 >= notch_r:
            right_edge = min(right_edge, x0)
        elif x1 <= notch_l:
            left_edge = max(left_edge, x1)
    return max(0.0, notch_l - left_edge - GAP), max(0.0, right_edge - notch_r - GAP)


def choose(left_free, right_free, left_known=True, right_known=True, side="auto"):
    """side 是用户的手动选择：auto（自动避让）/ left / right。"""
    if side == "left":
        return {"mode": "left", "lw": WING_MAX + 16, "rw": 0}
    if side == "right":
        return {"mode": "right", "lw": 0, "rw": WING_MAX + 16}
    lf = left_free if left_known else 0
    rf = right_free if right_known else 0
    if rf >= NEED_PCT and lf >= NEED_DOT:
        return {"mode": "wings", "lw": int(min(lf, WING_MAX)), "rw": int(min(rf, WING_MAX))}
    if lf >= NEED_BOTH:
        return {"mode": "left", "lw": int(min(lf, WING_MAX + 24)), "rw": 0}
    if rf >= NEED_PCT:
        return {"mode": "right", "lw": 0, "rw": int(min(rf, WING_MAX + 24))}
    return {"mode": "none", "lw": 0, "rw": 0}


def layout(notch_l, notch_r, scr_l, scr_r, obstacles, left_known=True, right_known=True, side="auto"):
    lf, rf = free_space(notch_l, notch_r, scr_l, scr_r, obstacles)
    out = choose(lf, rf, left_known, right_known, side if side in SIDES else "auto")
    out.update(left_free=round(lf), right_free=round(rf))
    return out


def pill_frame(lay, notch_l, notch_r, top, ih):
    """返回 (x, y, w, h)，坐标系与 NSScreen 相同（y 向上）；返回 None 表示不显示岛。
    岛的高度永远等于菜单栏高度，不会伸到菜单栏下方。"""
    nw = notch_r - notch_l
    if lay["mode"] == "none":
        return (notch_l, top - ih, nw, ih) if nw > 0 else None
    return notch_l - lay["lw"], top - ih, nw + lay["lw"] + lay["rw"], ih
