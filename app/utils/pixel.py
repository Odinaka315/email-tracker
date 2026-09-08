# 43-byte Transparent 1x1 GIF
TRANSPARENT_1X1_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"
    b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

TRACKING_PIXEL_HEADERS = {
    "Content-Type": "image/gif",
    "Content-Length": str(len(TRANSPARENT_1X1_GIF)),
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, private",
    "Pragma": "no-cache",
    "Expires": "0",
    "Access-Control-Allow-Origin": "*",
}
