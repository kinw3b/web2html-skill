#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  validate-visual.sh \
    --reference <path> \
    --implementation <path> \
    --profile <lenient|portable|strict|ultra> \
    [--sections <sections.json>] \
    [--text-checks <text_checks.json>] \
    [--spacing-checks <spacing_checks.json>] \
    [--color-checks <color_checks.json>] \
    [--output <report.json>]

Input JSON schemas:
  sections.json: [
    {"id":"header","x":0,"y":0,"width":390,"height":88}
  ]

  text_checks.json: [
    {"id":"title_baseline","reference":214,"implementation":216}
  ]

  spacing_checks.json: [
    {"id":"header_to_card","reference":24,"implementation":26}
  ]

  color_checks.json: [
    {"id":"text_primary","x":40,"y":72}
  ]
USAGE
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 2
  }
}

IM_MODE=""
IM_CONVERT=()
IM_COMPARE=()
IM_IDENTIFY=()

detect_imagemagick() {
  if command -v magick >/dev/null 2>&1; then
    IM_MODE="magick"
    IM_CONVERT=(magick convert)
    IM_COMPARE=(magick compare)
    IM_IDENTIFY=(magick identify)
    return
  fi
  if command -v convert >/dev/null 2>&1 && command -v compare >/dev/null 2>&1 && command -v identify >/dev/null 2>&1; then
    IM_MODE="im6"
    IM_CONVERT=(convert)
    IM_COMPARE=(compare)
    IM_IDENTIFY=(identify)
    return
  fi
  echo "Missing ImageMagick commands. Need either 'magick' (v7) or 'convert'+'compare'+'identify' (v6)." >&2
  exit 2
}

im_identify_dims() {
  local image="$1"
  "${IM_IDENTIFY[@]}" -format '%w %h' "$image"
}

im_crop() {
  local input="$1"
  local geometry="$2"
  local output="$3"
  "${IM_CONVERT[@]}" "$input" -crop "$geometry" +repage "$output"
}

im_pixel_at() {
  local image="$1"
  local x="$2"
  local y="$3"
  "${IM_CONVERT[@]}" "$image" -format "%[pixel:p{$x,$y}]" info:
}

im_rgb_to_lab_255() {
  local r="$1"
  local g="$2"
  local b="$3"
  "${IM_CONVERT[@]}" -size 1x1 "xc:rgb($r,$g,$b)" -colorspace Lab -format "%[fx:int(255*r)] %[fx:int(255*g)] %[fx:int(255*b)]" info:
}

to_percent() {
  local numerator="$1"
  local denominator="$2"
  awk -v n="$numerator" -v d="$denominator" 'BEGIN { if (d == 0) print 0; else printf "%.6f", (n / d) * 100 }'
}

abs_diff() {
  local a="$1"
  local b="$2"
  awk -v x="$a" -v y="$b" 'BEGIN { d = x - y; if (d < 0) d = -d; printf "%.6f", d }'
}

metric_ae() {
  local ref="$1"
  local imp="$2"
  local out
  out=$("${IM_COMPARE[@]}" -metric AE "$ref" "$imp" null: 2>&1 >/dev/null || true)
  awk 'END { for (i = NF; i >= 1; i--) if ($i ~ /^[0-9]+(\.[0-9]+)?$/) { print $i; found = 1; break } if (!found) print 0 }' <<<"$out"
}

rgb_at() {
  local image="$1"
  local x="$2"
  local y="$3"
  local px
  px=$(im_pixel_at "$image" "$x" "$y")
  if [[ "$px" =~ rgba?\(([0-9]+),([0-9]+),([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]} ${BASH_REMATCH[3]}"
  elif [[ "$px" =~ srgba?\(([0-9]+),([0-9]+),([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]} ${BASH_REMATCH[3]}"
  elif [[ "$px" =~ gray\(([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[1]} ${BASH_REMATCH[1]}"
  else
    echo "0 0 0"
  fi
}

rgb_to_lab_255() {
  local r="$1"
  local g="$2"
  local b="$3"
  im_rgb_to_lab_255 "$r" "$g" "$b"
}

delta_e_76() {
  local r1="$1" g1="$2" b1="$3"
  local r2="$4" g2="$5" b2="$6"
  local l1a1b1 l2a2b2
  l1a1b1=$(rgb_to_lab_255 "$r1" "$g1" "$b1")
  l2a2b2=$(rgb_to_lab_255 "$r2" "$g2" "$b2")

  local L1_255 a1_255 b1_255 L2_255 a2_255 b2_255
  read -r L1_255 a1_255 b1_255 <<<"$l1a1b1"
  read -r L2_255 a2_255 b2_255 <<<"$l2a2b2"

  awk -v L1p="$L1_255" -v A1p="$a1_255" -v B1p="$b1_255" -v L2p="$L2_255" -v A2p="$a2_255" -v B2p="$b2_255" '
    BEGIN {
      L1 = (L1p / 255.0) * 100.0; A1 = A1p - 128.0; B1 = B1p - 128.0;
      L2 = (L2p / 255.0) * 100.0; A2 = A2p - 128.0; B2 = B2p - 128.0;
      dL = L1 - L2; dA = A1 - A2; dB = B1 - B2;
      printf "%.6f", sqrt((dL*dL) + (dA*dA) + (dB*dB));
    }
  '
}

is_leq() {
  local value="$1"
  local threshold="$2"
  awk -v v="$value" -v t="$threshold" 'BEGIN { if (v <= t) print "true"; else print "false" }'
}

REF=""
IMP=""
PROFILE=""
SECTIONS_FILE=""
TEXT_FILE=""
SPACING_FILE=""
COLOR_FILE=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reference)
      REF="$2"
      shift 2
      ;;
    --implementation)
      IMP="$2"
      shift 2
      ;;
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --sections)
      SECTIONS_FILE="$2"
      shift 2
      ;;
    --text-checks)
      TEXT_FILE="$2"
      shift 2
      ;;
    --spacing-checks)
      SPACING_FILE="$2"
      shift 2
      ;;
    --color-checks)
      COLOR_FILE="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$REF" && -n "$IMP" && -n "$PROFILE" ]] || {
  usage
  exit 2
}

require_cmd jq
require_cmd awk
detect_imagemagick

case "$PROFILE" in
  lenient)
    T_GLOBAL="3.5"
    T_SECTION="2.5"
    T_TEXT="3"
    T_SPACING="2"
    T_COLOR="4"
    ;;
  portable)
    T_GLOBAL="1.5"
    T_SECTION="1.0"
    T_TEXT="2"
    T_SPACING="1"
    T_COLOR="2.5"
    ;;
  strict)
    T_GLOBAL="0.8"
    T_SECTION="0.5"
    T_TEXT="1"
    T_SPACING="1"
    T_COLOR="1.5"
    ;;
  ultra)
    T_GLOBAL="0.4"
    T_SECTION="0.25"
    T_TEXT="0.5"
    T_SPACING="0.5"
    T_COLOR="1.0"
    ;;
  *)
    echo "Unknown profile: $PROFILE" >&2
    exit 2
    ;;
esac

read -r ref_w ref_h <<<"$(im_identify_dims "$REF")"
read -r imp_w imp_h <<<"$(im_identify_dims "$IMP")"
if [[ "$ref_w" != "$imp_w" || "$ref_h" != "$imp_h" ]]; then
  echo "Reference and implementation image dimensions differ: ${ref_w}x${ref_h} vs ${imp_w}x${imp_h}" >&2
  exit 2
fi

total_pixels=$((ref_w * ref_h))
global_diff_pixels=$(metric_ae "$REF" "$IMP")
global_diff_percent=$(to_percent "$global_diff_pixels" "$total_pixels")
global_pass=$(is_leq "$global_diff_percent" "$T_GLOBAL")

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

sections_jsonl="$tmpdir/sections.jsonl"
text_jsonl="$tmpdir/text.jsonl"
spacing_jsonl="$tmpdir/spacing.jsonl"
color_jsonl="$tmpdir/color.jsonl"
: >"$sections_jsonl"
: >"$text_jsonl"
: >"$spacing_jsonl"
: >"$color_jsonl"

if [[ -n "$SECTIONS_FILE" ]]; then
  jq -c '.[]' "$SECTIONS_FILE" | while read -r row; do
    id=$(jq -r '.id' <<<"$row")
    x=$(jq -r '.x' <<<"$row")
    y=$(jq -r '.y' <<<"$row")
    w=$(jq -r '.width' <<<"$row")
    h=$(jq -r '.height' <<<"$row")

    ref_crop="$tmpdir/ref_${id}.png"
    imp_crop="$tmpdir/imp_${id}.png"

    im_crop "$REF" "${w}x${h}+${x}+${y}" "$ref_crop"
    im_crop "$IMP" "${w}x${h}+${x}+${y}" "$imp_crop"

    diff_pixels=$(metric_ae "$ref_crop" "$imp_crop")
    section_pixels=$((w * h))
    diff_percent=$(to_percent "$diff_pixels" "$section_pixels")
    pass=$(is_leq "$diff_percent" "$T_SECTION")

    jq -n \
      --arg id "$id" \
      --argjson x "$x" \
      --argjson y "$y" \
      --argjson width "$w" \
      --argjson height "$h" \
      --argjson diff_pixels "$diff_pixels" \
      --argjson diff_percent "$diff_percent" \
      --argjson threshold "$T_SECTION" \
      --argjson pass "$pass" \
      '{
        id: $id,
        region: {x: $x, y: $y, width: $width, height: $height},
        diff_pixels: $diff_pixels,
        diff_percent: $diff_percent,
        threshold_percent: $threshold,
        pass: $pass
      }' >>"$sections_jsonl"
  done
fi

if [[ -n "$TEXT_FILE" ]]; then
  jq -c '.[]' "$TEXT_FILE" | while read -r row; do
    id=$(jq -r '.id' <<<"$row")
    ref_v=$(jq -r '.reference' <<<"$row")
    imp_v=$(jq -r '.implementation' <<<"$row")
    drift=$(abs_diff "$ref_v" "$imp_v")
    pass=$(is_leq "$drift" "$T_TEXT")

    jq -n \
      --arg id "$id" \
      --argjson reference "$ref_v" \
      --argjson implementation "$imp_v" \
      --argjson drift "$drift" \
      --argjson threshold "$T_TEXT" \
      --argjson pass "$pass" \
      '{id: $id, reference: $reference, implementation: $implementation, drift_px: $drift, threshold_px: $threshold, pass: $pass}' >>"$text_jsonl"
  done
fi

if [[ -n "$SPACING_FILE" ]]; then
  jq -c '.[]' "$SPACING_FILE" | while read -r row; do
    id=$(jq -r '.id' <<<"$row")
    ref_v=$(jq -r '.reference' <<<"$row")
    imp_v=$(jq -r '.implementation' <<<"$row")
    drift=$(abs_diff "$ref_v" "$imp_v")
    pass=$(is_leq "$drift" "$T_SPACING")

    jq -n \
      --arg id "$id" \
      --argjson reference "$ref_v" \
      --argjson implementation "$imp_v" \
      --argjson drift "$drift" \
      --argjson threshold "$T_SPACING" \
      --argjson pass "$pass" \
      '{id: $id, reference: $reference, implementation: $implementation, drift_px: $drift, threshold_px: $threshold, pass: $pass}' >>"$spacing_jsonl"
  done
fi

if [[ -n "$COLOR_FILE" ]]; then
  jq -c '.[]' "$COLOR_FILE" | while read -r row; do
    id=$(jq -r '.id' <<<"$row")
    x=$(jq -r '.x' <<<"$row")
    y=$(jq -r '.y' <<<"$row")

    read -r rr rg rb <<<"$(rgb_at "$REF" "$x" "$y")"
    read -r ir ig ib <<<"$(rgb_at "$IMP" "$x" "$y")"

    de=$(delta_e_76 "$rr" "$rg" "$rb" "$ir" "$ig" "$ib")
    pass=$(is_leq "$de" "$T_COLOR")

    jq -n \
      --arg id "$id" \
      --argjson x "$x" \
      --argjson y "$y" \
      --argjson reference_rgb "[$rr,$rg,$rb]" \
      --argjson implementation_rgb "[$ir,$ig,$ib]" \
      --argjson delta_e "$de" \
      --argjson threshold "$T_COLOR" \
      --argjson pass "$pass" \
      '{id: $id, sample: {x: $x, y: $y}, reference_rgb: $reference_rgb, implementation_rgb: $implementation_rgb, delta_e: $delta_e, threshold_delta_e: $threshold, pass: $pass}' >>"$color_jsonl"
  done
fi

sections_array='[]'
text_array='[]'
spacing_array='[]'
color_array='[]'
[[ -s "$sections_jsonl" ]] && sections_array=$(jq -s '.' "$sections_jsonl")
[[ -s "$text_jsonl" ]] && text_array=$(jq -s '.' "$text_jsonl")
[[ -s "$spacing_jsonl" ]] && spacing_array=$(jq -s '.' "$spacing_jsonl")
[[ -s "$color_jsonl" ]] && color_array=$(jq -s '.' "$color_jsonl")

summary_json=$(jq -n \
  --arg profile "$PROFILE" \
  --argjson ref_w "$ref_w" \
  --argjson ref_h "$ref_h" \
  --argjson t_global "$T_GLOBAL" \
  --argjson t_section "$T_SECTION" \
  --argjson t_text "$T_TEXT" \
  --argjson t_spacing "$T_SPACING" \
  --argjson t_color "$T_COLOR" \
  --argjson global_diff_pixels "$global_diff_pixels" \
  --argjson global_diff_percent "$global_diff_percent" \
  --argjson global_pass "$global_pass" \
  --argjson sections "$sections_array" \
  --argjson text_checks "$text_array" \
  --argjson spacing_checks "$spacing_array" \
  --argjson color_checks "$color_array" \
  '{
    profile: $profile,
    image_dimensions: {width: $ref_w, height: $ref_h},
    thresholds: {
      global_percent: $t_global,
      section_percent: $t_section,
      text_drift_px: $t_text,
      spacing_drift_px: $t_spacing,
      color_delta_e: $t_color
    },
    global: {
      diff_pixels: $global_diff_pixels,
      diff_percent: $global_diff_percent,
      threshold_percent: $t_global,
      pass: $global_pass
    },
    sections: $sections,
    text_checks: $text_checks,
    spacing_checks: $spacing_checks,
    color_checks: $color_checks,
    pass: (
      $global_pass and
      (($sections | all(.[]?; .pass)) // true) and
      (($text_checks | all(.[]?; .pass)) // true) and
      (($spacing_checks | all(.[]?; .pass)) // true) and
      (($color_checks | all(.[]?; .pass)) // true)
    )
  }')

if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "$summary_json" >"$OUTPUT"
else
  printf '%s\n' "$summary_json"
fi

echo "Profile: $PROFILE"
echo "Global diff: ${global_diff_percent}% (threshold ${T_GLOBAL}%)"

overall=$(jq -r '.pass' <<<"$summary_json")
echo "Overall pass: $overall"

if [[ "$overall" != "true" ]]; then
  exit 1
fi
exit 0

