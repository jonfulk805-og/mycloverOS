#!/bin/bash
# CloverOS Desktop Branding — applies wallpaper on first boot
# Called by cloverdesktop entrypoint or custom-cont-init.d

WALLPAPER_SRC="/branding/wallpaper.png"
WALLPAPER_DST="/config/.config/cloverOS-wallpaper.png"
XFCE_CHANNEL="/config/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml"

# Only copy wallpaper if not already in place
if [[ ! -f "$WALLPAPER_DST" ]] && [[ -f "$WALLPAPER_SRC" ]]; then
    mkdir -p "$(dirname "$WALLPAPER_DST")"
    cp "$WALLPAPER_SRC" "$WALLPAPER_DST"
    echo "[cloverOS] Wallpaper installed to $WALLPAPER_DST"
fi

# Set XFCE desktop wallpaper config (only if not already configured)
if [[ -f "$WALLPAPER_DST" ]] && [[ ! -f "$XFCE_CHANNEL" ]]; then
    mkdir -p "$(dirname "$XFCE_CHANNEL")"
    cat > "$XFCE_CHANNEL" << 'XFCEXML'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-desktop" version="1.0">
  <property name="backdrop" type="empty">
    <property name="screen0" type="empty">
      <property name="monitorscreen" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/config/.config/cloverOS-wallpaper.png"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.050980"/>
            <value type="double" value="0.066667"/>
            <value type="double" value="0.090196"/>
            <value type="double" value="1.000000"/>
          </property>
        </property>
      </property>
      <property name="monitorsscreen" type="empty">
        <property name="workspace0" type="empty">
          <property name="last-image" type="string" value="/config/.config/cloverOS-wallpaper.png"/>
          <property name="image-style" type="int" value="5"/>
          <property name="color-style" type="int" value="0"/>
          <property name="rgba1" type="array">
            <value type="double" value="0.050980"/>
            <value type="double" value="0.066667"/>
            <value type="double" value="0.090196"/>
            <value type="double" value="1.000000"/>
          </property>
        </property>
      </property>
    </property>
  </property>
</channel>
XFCEXML
    echo "[cloverOS] XFCE desktop wallpaper configured"
fi
