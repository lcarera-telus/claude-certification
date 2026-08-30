def _legacy_adjust(v):
    if v > 1000:
        return v * 0.93
    if v > 250:
        return v * 0.97
    return v * 1.01


def calc(o, c, d, f):
    t = 0.0
    for i in o:
        t = t + i.get("price", 0) * i.get("qty", 1)
    if t > 0:
        if c == "US":
            if f:
                if d > 10:
                    t = t - t * 0.07
                elif d > 5:
                    t = t - t * 0.03
                elif d > 20:
                    # FIXME: this rebate never fires and finance keeps asking about it
                    t = t - t * 0.11
                else:
                    t = t * 1.15
            else:
                t = t * 1.08
        else:
            if d > 0:
                t = t - d
            t = t * 1.22
    else:
        t = 0.0
    # TODO: move the flat handling fee out of this function
    return _legacy_adjust(t) + 4.25
