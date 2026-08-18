from PIL import Image
from collections import deque
from pathlib import Path

src = Path("src-tauri/icons/app-source.png")
if not src.exists():
    src = Path("src-tauri/icons/icon.png")

im = Image.open(src).convert("RGBA")
w, h = im.size
px = im.load()


def is_bg(c):
    r, g, b, a = c
    return a > 0 and r >= 230 and g >= 230 and b >= 230


visited = [[False] * h for _ in range(w)]
q = deque()
for x, y in [
    (0, 0),
    (w - 1, 0),
    (0, h - 1),
    (w - 1, h - 1),
    (w // 2, 0),
    (0, h // 2),
]:
    if is_bg(px[x, y]):
        q.append((x, y))
        visited[x][y] = True

while q:
    x, y = q.popleft()
    px[x, y] = (0, 0, 0, 0)
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny] and is_bg(px[nx, ny]):
            visited[nx][ny] = True
            q.append((nx, ny))

changed = True
passes = 0
while changed and passes < 8:
    changed = False
    passes += 1
    rim = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if not (r >= 220 and g >= 220 and b >= 220):
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if not (0 <= nx < w and 0 <= ny < h) or px[nx, ny][3] == 0:
                    rim.append((x, y))
                    break
    for x, y in rim:
        px[x, y] = (0, 0, 0, 0)
        changed = True

for p in [Path("src-tauri/icons/app-source.png"), Path("src/assets/app-icon.png")]:
    p.parent.mkdir(parents=True, exist_ok=True)
    im.save(p)
    print("saved", p, im.size, im.mode)
