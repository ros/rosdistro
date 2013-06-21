gource ..  -s 0.02 -o /tmp/gource_output.ppm --title "rosdistro"

ffmpeg -y -b 3000K -r 60 -f image2pipe -vcodec ppm -i /tmp/gource_output.ppm -vcodec libx264 /tmp/gource.mp4