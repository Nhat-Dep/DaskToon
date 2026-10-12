// SPDX-FileCopyrightText: 2026 DaskToon Authors
// SPDX-License-Identifier: GPL-2.0-or-later
// Written by DaskToon's Engine Export; exporting again replaces it.

using UnityEditor;
using UnityEngine;

namespace DaskToon.Editor
{
    /// <summary>Keeps the anime timing of a DaskToon clip (anime timing spec 5). The clip file (marked
    /// "DaskToonStepped") already holds every drawing for its frames; its keys are made constant, so the game switches
    /// pose on the drawn frames instead of easing between them.</summary>
    public class DaskToonClipImporter : AssetPostprocessor
    {
        public const string SteppedMark = "DaskToonStepped";

        void OnPostprocessAnimation(GameObject root, AnimationClip clip)
        {
            if (!DaskToonAvatarImporter.HasMark(assetImporter.userData, SteppedMark)) return;
            foreach (var binding in AnimationUtility.GetCurveBindings(clip))
            {
                var curve = AnimationUtility.GetEditorCurve(clip, binding);
                if (curve == null) continue;
                for (var i = 0; i < curve.length; i++)
                {
                    AnimationUtility.SetKeyLeftTangentMode(curve, i, AnimationUtility.TangentMode.Constant);
                    AnimationUtility.SetKeyRightTangentMode(curve, i, AnimationUtility.TangentMode.Constant);
                }
                AnimationUtility.SetEditorCurve(clip, binding, curve);
            }
        }
    }
}
