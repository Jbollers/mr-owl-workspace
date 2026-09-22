# Project skills

Nineteen skills live in this project. `.agents/skills` is the maintained source
for Codex; `.claude/skills` contains complete, identical copies for Claude Code,
including scripts and references. Both Skills sections open the full instructions.
These are local project files, not global installations.

Claude reads the instructions in its own `SKILL.md` when a skill is used; a
Markdown link is just a request to read another file, not automatic inheritance.
The template includes full folders so a normal Windows clone needs no symlinks.
See [Claude's skill format](https://code.claude.com/docs/en/skills).

For shared changes, edit `.agents/skills`, then run `npm run skills:sync`.
If you edited a Claude copy directly, first move that intended change into the
maintained source. `npm run test:template` checks that the two copies agree.

| Skill | Use it for |
| --- | --- |
| [3d-production-routing](../.agents/skills/3d-production-routing/SKILL.md) | Choose a practical workflow for 3D concepts, generated meshes, material maps, procedural Three.js reconstruction and game animation. |
| [blender-game-animation](../.agents/skills/blender-game-animation/SKILL.md) | Rig and animate supplied characters in Blender, revise motion from references, and deliver editable sources plus a verified game export. |
| [character-sheet-pipeline](../.agents/skills/character-sheet-pipeline/SKILL.md) | Prepare strict-front character sheets, isolated parts and optional multiview references for 3D modeling from an approved image. |
| [fal-ai-generation](../.agents/skills/fal-ai-generation/SKILL.md) | Generate and edit images, create video, audio, 3D assets or material maps through fal.ai MCP or the Python queue client. Use for fal model discovery, reference uploads, generation, recovery and local delivery. |
| [feature-handoff](../.agents/skills/feature-handoff/SKILL.md) | Prepare a precise handoff for an agent or developer implementing a feature, continuing a task or reviewing a finished change. |
| [higgsfield-workflow](../.agents/skills/higgsfield-workflow/SKILL.md) | Use the official Higgsfield CLI or its Blender integration to discover models, generate requested assets and resume recorded jobs. |
| [image-reference-workflow](../.agents/skills/image-reference-workflow/SKILL.md) | Explore image concepts and make faithful edits of accepted references for 3D or creative production, with explicit model choices and visual review. |
| [img2threejs](../.agents/skills/img2threejs/SKILL.md) | Turn an object or character reference image into a quality-gated, animation-ready procedural Three.js model built in code. Use for image-to-3D reconstruction, detail-accurate object rebuilds, stylized/likeness-maximized human characters, sculpt specs, and staged code generation. |
| [materials-to-game](../.agents/skills/materials-to-game/SKILL.md) | Create or apply material maps and bake a textured high-poly mesh onto a game mesh, with channel, UV and export checks. |
| [motion-reference-workflow](../.agents/skills/motion-reference-workflow/SKILL.md) | Prepare and select character motion references, or transfer approved motion to a human reference for a later mocap workflow. |
| [plan](../.agents/skills/plan/SKILL.md) | Turn a broad project request into a small actionable plan with concrete deliverables, dependencies and acceptance checks. |
| [video-watch](../.agents/skills/video-watch/SKILL.md) | Inspect a local or publicly accessible video through sampled scene frames, timestamps and a visual report, especially for motion and 3D reference analysis. |
| [voice-dictation-setup](../.agents/skills/voice-dictation-setup/SKILL.md) | Help configure optional local Whisper dictation into terminals and other apps, with language, hotkey and CPU or GPU checks. |
| [workspace-authoring](../.agents/skills/workspace-authoring/SKILL.md) | Create or maintain Workspace cards, report tabs and Markdown deliverables with consistent styling, working media previews and clear project organization. |

The eight creative modules can be copied together with their local resources:
fal-ai-generation, image-reference-workflow, character-sheet-pipeline,
higgsfield-workflow, img2threejs, materials-to-game, motion-reference-workflow
and blender-game-animation. Keep the full img2threejs folder and its licenses.

Workspace authoring, video inspection and dictation setup also reference this
repository's processes, knowledge and scripts. Copy those referenced files when
extracting a module, or share the full template. Planning and handoff skills use
the local project conventions rather than another person's memory.

A skill does not authenticate a provider or install a tool. Follow its setup
references and bring your own account. Credentials and raw paid-job receipts
must stay outside a shared skill pack.

## Mr. Bollers’ teaching skills

- [Plan a lesson](../.agents/skills/elementary-lesson-plan-builder/SKILL.md): Build from a topic, teacher guide or curriculum.
- [Format a plan](../.agents/skills/lesson-plan-template-formatter/SKILL.md): Put approved content into your teacher-facing layout.
- [Adapt a deck](../.agents/skills/powerpoint-lesson-editor/SKILL.md): Make room for the learning that matters.
- [Add teacher notes](../.agents/skills/powerpoint-teacher-notes-generator/SKILL.md): Keep your next question and scaffold close at hand.
- [Bring it indoors](../.agents/skills/shorten-lesson-deck/SKILL.md): Turn an outdoor task into useful classroom evidence.

See [the teaching workflow](../processes/teaching.md) for routing, timing preferences and file-tool requirements.
