ROSDISTRO=jade

cp -r rosdistro filtered_rosdistro
(cd filtered_rosdistro && git filter-branch --subdirectory-filter $ROSDISTRO -- --all)
gource filtered_rosdistro --stop-at-end -s 0.25 -o gource_output.ppm --title "$ROSDISTRO Release Preparations"
avconv -y -b 6000K -r 60 -f image2pipe -vcodec ppm -i gource_output.ppm -vcodec libx264 $ROSDISTRO_release_preparations.mp4
