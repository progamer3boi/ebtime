# ebtime — 0.1.0 preview

Draggable DaVinci Resolve / Fusion retiming effect with an **Open Editor** button and a companion Lua preset editor. Original code, using the node approach demonstrated by your supplied setting; no third-party branding or embedded artwork copied.

## Install

1. Extract this ZIP into a permanent folder. Close Resolve.
2. With Python 3 installed, run `python install.py` (Windows), or `python3 install.py` (macOS/Linux). The installer copies the editor, Edit effect and Fusion macro into your current user's Resolve Fusion folder. Existing ebtime files receive `.bak` backups.
3. Restart Resolve. Find **ebtime** in Edit → Effects Library → Fusion Effects. In Fusion, find it under Templates or add the macro through the tool search, depending on Resolve version.

For a custom installation use `python install.py --fusion-root "path/to/Fusion"`.

Default Fusion folders:

- Windows: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion`
- macOS: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion`
- Linux: `~/.local/share/DaVinciResolve/Fusion`

Manual install: copy the supplied `Templates` and `Scripts` folders into that Fusion folder. Copy `ebtime.setting` into `Fusion/Macros` too if desired. The uninstalled template resolves the editor via `Scripts:Comp/ebtime Editor.lua`; if that path map points elsewhere, run the editor from Workspace → Scripts → Comp instead. The installer embeds the exact editor location to avoid this ambiguity.

## Use

1. Prefer an ordinary video clip or a **compound clip** with enough source frames/handles. Apply ebtime on the Edit page. In Fusion, insert the macro between MediaIn and MediaOut.
2. Open the Fusion page, select ebtime, and click **Open Editor** in the Inspector. Select the effect instance if your composition contains more than one. Alternatively run Workspace → Scripts → Comp → ebtime Editor.
3. Select one of 25 presets. The preview is a **source-position graph**, not a speed graph: rising plays forwards, horizontal holds, falling reverses. The slope gives speed.
4. Set Source start/end in **Fusion source-frame coordinates**. Defaults use the composition render range. If your source starts on another frame, set these explicitly. The effect maps over the current composition render range.
5. Curve amount blends the preset with normalised linear playback. Source travel multiplies the resulting source-position range, anchored at Source start. Four Bezier controls are available for Ease in, Ease out, S curve and Custom Bezier.
6. Choose interpolation, then Apply. It replaces this effect's Source Time animation with one sampled keyframe per output frame. Preview and use Resolve Undo to revert. After changing clip duration/render range, reopen the editor and apply again.

Preset selection previews a graph; **Apply** changes the clip. Reset controls resets the editor only; choose Normal/reset and Apply to restore linear timing. Editor settings are not reloaded from previously applied curves on reopening.

## Presets

Normal; 50%, 25%, 10% slow motion; 2x and 4x fast; reverse; half-speed reverse; middle freeze; freeze then go; go then freeze; mid-shot freeze; ease in; ease out; smooth S; fast-slow-fast; slow-fast-slow; impact slowdown; launch ramp; boomerang; reverse then forward; triple shuttle; stutter steps; pulse ramp; custom Bezier.

## Compatibility and limits

- **Preview build, not tested inside Resolve.** Lua syntax, graph formulas, package structure and installer were checked externally. The UIManager API, macro button execution and playback still require a Resolve smoke test. No specific Resolve version or Free/Studio edition is certified.
- The pop-up requires Fusion **UIManager/UIDispatcher** scripting support. Availability varies with Resolve version/edition. If the button is blocked on the Edit page, use it on the Fusion page or launch the script from the menu. An Edit-page pop-up is not guaranteed by a `.setting` template.
- Uses native Dimension Optical Flow + Time Stretcher. **Twixtor and Speed Warp are not included.** Native optical flow can distort occlusions, fast motion and scene cuts; no preset can guarantee clean extreme slow motion.
- Adjustment clips can expose only the composited frame at the current time rather than the temporal source frames a retimer needs. **Adjustment-clip retiming is not guaranteed.** If frames freeze, use a compound clip and apply ebtime directly to it; render-in-place first if needed.
- It cannot create missing footage, extend a clip's duration, retime audio or change Edit-page timeline speed metadata. Beyond available source frames, edge clamping may produce a freeze. 2x/4x presets need additional source frames.
- The graph is a text plot in a native Resolve window. Custom curve editing uses numerical Bezier controls, not draggable graph handles. Presets are sampled to frame keys; very long clips can be costly (100,000-frame cap).
- UIManager windows run a dispatcher loop: close the editor to return to normal editing. Failed Apply operations unlock the composition; use Undo if a partial change remains.

## Quick in-Resolve smoke test

Use a numbered test clip. Confirm Normal gives matching frames; Reverse maps first output to Source end; 50% reaches halfway through the source range; Freeze middle holds the midpoint. Try Apply/Undo, reopen, two ebtime instances, a non-zero render start, and all three interpolation modes. Then test a compound clip and the Edit effect on your Resolve version.

## Remove

Close Resolve and delete the installed `Templates/Edit/Effects/ebtime` folder, `Macros/ebtime.setting` and `Scripts/Comp/ebtime Editor.lua`. Restore `.bak` files if replacing an older installation.

## License

Original ebtime code in this package is provided under the MIT license (see LICENSE). DaVinci Resolve, Fusion and Twixtor are trademarks of their respective owners.
