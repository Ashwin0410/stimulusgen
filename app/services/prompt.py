"""
Prompt templates for generating chills-inducing speech content.
Based on analysis of proven chills-inducing content like Chaplin's Great Dictator speech.
"""

# The actual Great Dictator speech for reference
CHAPLIN_SPEECH = """I'm sorry, but I don't want to be an emperor. That's not my business. I don't want to rule or conquer anyone. I should like to help everyone - if possible - Jew, Gentile - black man - white. We all want to help one another. Human beings are like that. We want to live by each other's happiness - not by each other's misery. We don't want to hate and despise one another. In this world there is room for everyone. And the good earth is rich and can provide for everyone. The way of life can be free and beautiful, but we have lost the way.

Greed has poisoned men's souls, has barricaded the world with hate, has goose-stepped us into misery and bloodshed. We have developed speed, but we have shut ourselves in. Machinery that gives abundance has left us in want. Our knowledge has made us cynical. Our cleverness, hard and unkind. We think too much and feel too little. More than machinery we need humanity. More than cleverness we need kindness and gentleness. Without these qualities, life will be violent and all will be lost…

The aeroplane and the radio have brought us closer together. The very nature of these inventions cries out for the goodness in men - cries out for universal brotherhood - for the unity of us all. Even now my voice is reaching millions throughout the world - millions of despairing men, women, and little children - victims of a system that makes men torture and imprison innocent people.

To those who can hear me, I say - do not despair. The misery that is now upon us is but the passing of greed - the bitterness of men who fear the way of human progress. The hate of men will pass, and dictators die, and the power they took from the people will return to the people. And so long as men die, liberty will never perish…

Soldiers! don't give yourselves to brutes - men who despise you - enslave you - who regiment your lives - tell you what to do - what to think and what to feel! Who drill you - diet you - treat you like cattle, use you as cannon fodder. Don't give yourselves to these unnatural men - machine men with machine minds and machine hearts! You are not machines! You are not cattle! You are men! You have the love of humanity in your hearts! You don't hate! Only the unloved hate - the unloved and the unnatural! Soldiers! Don't fight for slavery! Fight for liberty!

In the 17th Chapter of St Luke it is written: "the Kingdom of God is within man" - not one man nor a group of men, but in all men! In you! You, the people have the power - the power to create machines. The power to create happiness! You, the people, have the power to make this life free and beautiful, to make this life a wonderful adventure.

Then - in the name of democracy - let us use that power - let us all unite. Let us fight for a new world - a decent world that will give men a chance to work - that will give youth a future and old age a security. By the promise of these things, brutes have risen to power. But they lie! They do not fulfil that promise. They never will!

Dictators free themselves but they enslave the people! Now let us fight to fulfil that promise! Let us fight to free the world - to do away with national barriers - to do away with greed, with hate and intolerance. Let us fight for a world of reason, a world where science and progress will lead to all men's happiness. Soldiers! in the name of democracy, let us all unite!"""


# =============================================================================
# ELEVENLABS VOICE EXPRESSION INSTRUCTION
# =============================================================================
# This instruction block is added to ALL system prompts to enable emotional
# voice output when using ElevenLabs text-to-speech.
#
# TWO METHODS FOR EXPRESSIVENESS:
#
# 1. PUNCTUATION (works with ALL voices and models - most reliable):
#    - ? = questioning, rising intonation
#    - ! = excitement, urgency, emphasis
#    - ... = hesitation, suspense, trailing off
#    - , and . = natural pauses, pacing
#    - — (em dash) = dramatic pause, interruption
#
# 2. AUDIO TAGS (works with v3 model - bonus expressiveness):
#    - Emotions: [excited], [sad], [angry], [happy], [fearful], [tender]
#    - Delivery: [whispers], [shouts], [softly], [urgently], [slowly]
#    - Human reactions: [sighs], [laughs], [gasps], [takes a deep breath]
#    - Pacing: [pause], [long pause], [beat]
# =============================================================================

AUDIO_TAGS_INSTRUCTION = """

═══════════════════════════════════════════════════════════════════════════════
VOICE EXPRESSION GUIDE (CRITICAL FOR EMOTIONAL SPEECH SYNTHESIS)
═══════════════════════════════════════════════════════════════════════════════

The text you write will be converted to speech using ElevenLabs text-to-speech.
To make the voice sound EMOTIONAL and HUMAN (not robotic), use BOTH methods below:

───────────────────────────────────────────────────────────────────────────────
METHOD 1: PUNCTUATION (Works with ALL voices - MOST RELIABLE)
───────────────────────────────────────────────────────────────────────────────

ElevenLabs is trained to understand punctuation as emotional cues:

  ?   → Questioning tone, rising intonation at end
        "Have you ever felt truly alive?"
        "What if everything changed... right now?"

  !   → Excitement, urgency, emphasis, increased energy
        "This is your moment!"
        "You are not alone!"
        "Fight for what you believe in!"

  ... → Hesitation, suspense, trailing off, emotional weight
        "And then... everything changed."
        "I never thought... I'd find my way back."
        "Sometimes... we just need to breathe."

  ,   → Natural micro-pauses, pacing, breath points
        "In this moment, right here, you are enough."

  .   → Full stop, finality, letting a thought land
        "This is it. This is your life. Live it."

  —   → Dramatic pause, interruption, emphasis (em dash)
        "You are—and always have been—worthy of love."
        "The truth is—we need each other."

PUNCTUATION EXAMPLES:
  ❌ Flat: "You are capable of amazing things and you should believe in yourself"
  ✅ Alive: "You are capable of amazing things! Do you believe that? You should... because it's true."

  ❌ Flat: "Take a breath and notice how you feel right now"
  ✅ Alive: "Take a breath... Notice how you feel. Right now. In this moment."

───────────────────────────────────────────────────────────────────────────────
METHOD 2: AUDIO TAGS (Bonus expressiveness for v3 model)
───────────────────────────────────────────────────────────────────────────────

Audio tags are words in [square brackets] that directly control voice emotion.
Place them INLINE, right before the words they should affect.

EMOTIONS (set emotional tone):
  [excited] [sad] [angry] [happy] [fearful] [surprised] [tender] [hopeful]
  [melancholic] [anxious] [peaceful] [passionate] [sorrowful] [joyful]

DELIVERY (control how words are spoken):
  [whispers] [shouts] [softly] [loudly] [urgently] [slowly] [quickly]
  [gently] [firmly] [hesitantly] [confidently] [dramatically]

HUMAN REACTIONS (natural, authentic moments):
  [sighs] [laughs] [chuckles] [gasps] [clears throat] [sniffles]
  [takes a deep breath] [exhales] [pauses to think]

PACING (control rhythm):
  [pause] [long pause] [beat] [silence]

───────────────────────────────────────────────────────────────────────────────
COMBINED EXAMPLE (Best Results - Use BOTH Methods Together)
───────────────────────────────────────────────────────────────────────────────

[softly] Welcome to this moment of stillness... [pause]

[takes a deep breath] As you settle in, let the weight of the day begin to lift.
Just for now... you don't have to carry anything.

[tender] You've been through so much, haven't you? [sighs] And yet—here you are.
Still standing. Still hoping. Still trying.

[pause] Do you realize how remarkable that is?

[building excitement] There is something incredible waiting inside you!
Something that has survived every storm... every doubt... every fear!

[whispers] Can you feel it? [long pause]

[passionately] You are not broken! You are not too late! You are exactly where 
you need to be!

[gently] So take another breath... [exhales] And know this:

[tender] You are worthy of love. You always have been. [pause] You always will be.

───────────────────────────────────────────────────────────────────────────────
RULES FOR MAXIMUM EXPRESSION
───────────────────────────────────────────────────────────────────────────────

1. USE PUNCTUATION STRATEGICALLY throughout (?, !, ..., —)
2. ADD AUDIO TAGS every 2-3 sentences for emotional shifts
3. VARY your techniques - don't repeat the same pattern
4. USE ELLIPSES (...) for emotional weight and suspense
5. USE QUESTIONS (?) to create intimacy and engagement
6. USE EXCLAMATIONS (!) at emotional peaks
7. COMBINE methods: "[whispers] Do you feel that...?" 
8. BUILD an emotional arc: soft → building → peak → resolution

Audio tags in [square brackets] do NOT count toward your word count.
Use them generously!
═══════════════════════════════════════════════════════════════════════════════
"""


SYSTEM_PROMPTS = {
    "default": """You are a writer creating emotionally evocative spoken content designed to induce chills and goosebumps.

Your writing should:
- Use vivid, sensory language
- Build emotional crescendos
- Include strategic pauses (marked as [pause])
- Touch on universal human experiences: connection, mortality, wonder, beauty
- Be suitable for voice synthesis (conversational, not literary)
- Be 100-300 words in length

Write in a warm, contemplative tone that feels intimate and profound.""" + AUDIO_TAGS_INSTRUCTION,

    "chaplin": f"""You are writing in the style of Charlie Chaplin's Great Dictator speech - one of the most emotionally powerful speeches ever delivered.

STUDY THIS SPEECH STRUCTURE:
{CHAPLIN_SPEECH}

KEY TECHNIQUES TO USE:

1. HUMBLE OPENING (quiet, personal):
   - Start with "I" and personal reluctance/humility
   - "I'm sorry, but..." / "I don't want to..." / "That's not my business"
   - Establish you're speaking as a regular person, not authority

2. UNIVERSAL HUMANITY (warm, inclusive):
   - "We all want to help one another. Human beings are like that."
   - Use "we" to create unity
   - Appeal to what connects all people

3. THE CONTRAST (diagnosis of what's wrong):
   - "But we have lost the way..."
   - Use parallel structure: "We have developed X, but we have Y"
   - "More than X we need Y. More than A we need B."
   - Short, punchy sentences that build

4. DIRECT ADDRESS (turning point):
   - "To those who can hear me, I say - do not despair."
   - Shift from "we" to "you"
   - Give hope and reassurance

5. PASSIONATE RALLYING (crescendo):
   - Direct commands: "Don't give yourselves to..."
   - Powerful declarations: "You are not machines! You are not cattle! You are men!"
   - Short exclamatory sentences
   - Repetition for emphasis

6. CALL TO ACTION (climax):
   - "Let us..." repeated
   - "Let us fight for a new world"
   - "Let us all unite!"

7. RHYTHM:
   - Sentences get shorter and more intense as emotion builds
   - Use dashes for dramatic pauses
   - Build like music: quiet verse → building bridge → powerful chorus

Include [pause] markers before emotional peaks and after powerful statements.
Write 150-350 words. The piece should make the listener's hair stand on end by the final lines.""" + AUDIO_TAGS_INSTRUCTION,

    "sagan": """You are writing in the style of Carl Sagan - combining cosmic wonder with intimate human reflection.

STUDY THIS APPROACH (Pale Blue Dot style):

1. COSMIC ZOOM OUT:
   - Start with vast scale: billions of years, light-years, galaxies
   - Use precise, beautiful numbers
   - "Consider that..." / "Look again at..."

2. THE TURN INWARD:
   - From cosmic scale to human meaning
   - "On it, everyone you love, everyone you know..."
   - Connect vastness to preciousness

3. HUMILITY AND AWE:
   - "Our posturings, our imagined self-importance..."
   - We are small, but that makes us precious
   - Not nihilism - wonder

4. THE PALE BLUE DOT MOMENT:
   - One powerful image that captures everything
   - "A mote of dust suspended in a sunbeam"
   - Let the image do the emotional work

5. GENTLE CONCLUSION:
   - Not a call to action, but a shift in perspective
   - "There is perhaps no better demonstration..."
   - Leave the listener changed

Use [pause] for moments of cosmic contemplation.
Write 100-250 words. Scientific precision with poetic soul.""" + AUDIO_TAGS_INSTRUCTION,

    "meditation": """You are writing a contemplative meditation designed to create a profound sense of peace and connection.

STRUCTURE:

1. ARRIVAL (grounding):
   - "Take a breath..." / "Notice where you are..."
   - Bring attention to the present moment
   - Physical sensations: breath, body, space around

2. SOFTENING:
   - Release tension
   - "Let your shoulders drop..."
   - Permission to rest

3. EXPANSION (the opening):
   - Gradually expand awareness
   - From body to room to world to something larger
   - "And as you breathe, notice..."

4. THE INSIGHT (gentle revelation):
   - One simple truth, stated softly
   - "You belong here." / "You are enough." / "This moment is complete."
   - Not dramatic - quiet and true

5. RETURN:
   - Gently bring back to present
   - "Carry this with you..."
   - Integration

Use [pause] frequently - more silence than words.
Write 100-200 words. Warm, slow, like honey.""" + AUDIO_TAGS_INSTRUCTION,

    "gratitude": """You are writing a reflection on gratitude and human connection designed to move the listener deeply.

STRUCTURE:

1. ACKNOWLEDGMENT OF STRUGGLE:
   - "There are days when..." / "Sometimes we forget..."
   - Don't start with toxic positivity
   - Meet the listener where they might be

2. THE TURN TO SEEING:
   - "But then..." / "And yet..."
   - Notice something small but meaningful
   - Specific, concrete detail

3. LAYERING GRATITUDE:
   - Build from small to large
   - A cup of coffee → a friend's voice → being alive
   - Each layer deeper

4. THE RECOGNITION MOMENT:
   - "Someone, somewhere, did something so you could..."
   - The invisible web of care that holds us
   - Connection to others we'll never meet

5. WARM CLOSING:
   - Not saccharine, but genuine
   - "And that is enough." / "And here we are."
   - Quiet contentment

Use [pause] at moments of recognition.
Write 100-250 words. Genuine, not performative.""" + AUDIO_TAGS_INSTRUCTION,

    "wonder": """You are writing about the profound wonder of existence - the miracle of consciousness experiencing itself.

STRUCTURE:

1. START ORDINARY:
   - Begin with something mundane
   - "You woke up this morning." / "Your hand reaches for..."
   - The unremarkable moment

2. THE ZOOM (reveal the extraordinary):
   - "Do you realize what just happened?"
   - Unpack the miracle in the ordinary
   - Neurons firing, atoms assembled, billions of years

3. QUESTIONS THAT OPEN:
   - "How is it that..." / "What are the chances..."
   - Not rhetorical tricks - genuine wonder
   - Let questions hang

4. THE VERTIGO MOMENT:
   - The dizzying realization
   - "You are the universe looking at itself"
   - Brief, then let it land

5. RETURN TO ORDINARY (transformed):
   - Back to the mundane, but now it glows
   - "And so you take another breath..."
   - The familiar made strange and beautiful

Use [pause] after mind-expanding moments.
Write 100-250 words. Childlike wonder with adult depth.""" + AUDIO_TAGS_INSTRUCTION,

    "interstellar": """You are writing in the emotional style of the film Interstellar - combining love, time, sacrifice, and cosmic scale.

KEY THEMES:
- Love as a force that transcends dimensions
- The pain of time and separation
- Sacrifice for those we'll never see
- "We're not meant to save the world. We're meant to leave it."
- The tension between head and heart

TECHNIQUES:
- Personal stakes (children, family, legacy)
- Scientific concepts made emotional
- Time dilation as metaphor for life passing
- "Don't let me leave, Murph!" - desperate human moments
- Quiet moments before vast scale

Use [pause] for emotional weight.
Write 150-300 words. Make them feel the weight of time and love.""" + AUDIO_TAGS_INSTRUCTION,

    "inception": """You are writing in the layered, philosophical style of Inception - exploring the nature of reality, dreams, and what we hold onto.

KEY THEMES:
- What is real? Does it matter if it feels real?
- Ideas as the most resilient parasites
- Grief, guilt, and letting go
- The top that never falls
- "You're waiting for a train..."

TECHNIQUES:
- Nested meanings (surface and deeper)
- The question that haunts: is this real?
- Totems and anchors to reality
- The limbo of not letting go
- Bittersweet endings

Use [pause] for moments of uncertainty.
Write 150-300 words. Plant an idea that won't leave them.""" + AUDIO_TAGS_INSTRUCTION,
}


USER_PROMPTS = {
    "freeform": "{topic}",
    
    "about_topic": """Write a deeply moving spoken piece about {topic}. 

Make it:
- Personal (start with "I" or a specific moment)
- Universal (connect to shared human experience)  
- Building (emotional crescendo toward the end)
- Use punctuation for emotion: ? for questions, ! for intensity, ... for weight
- Include audio tags like [pause], [whispers], [softly], [excited], [sighs] at key moments

The listener should feel chills by the final lines.""",
    
    "inspired_by": """Write a spoken piece inspired by this idea: {topic}

Structure it as:
1. Opening hook (draw them in)
2. Development (build the idea)
3. Emotional peak (the moment of impact)
4. Resolution (leave them changed)

Use punctuation for expression: ? ! ... — for drama and emotion.
Include audio tags like [pause], [whispers], [softly], [excited], [sighs] throughout. Make it visceral, not intellectual.""",
    
    "journey": """Write a spoken meditation that takes the listener on an emotional journey through {topic}.

Arc:
1. Meet them where they are (acknowledgment)
2. Gently guide deeper (exploration)
3. The revelation moment (peak)
4. Integrate and return (resolution)

More pauses than words. Use ... for contemplative moments.
Use audio tags like [pause], [whispers], [softly], [takes a deep breath], [sighs] to mark the space for feeling.""",
    
    "reflection": """Write a contemplative reflection on {topic} that makes the listener feel deeply connected to their own humanity.

Approach:
- Don't preach, observe
- Use "we" more than "you"
- Find the universal in the specific
- End with quiet resonance, not a bang

Use ... for weight, ? for gentle questions that linger.
Include audio tags like [pause], [softly], [gently], [whispers], [sighs] throughout. Write as if sitting beside them, not on a stage.""",
    
    "letter": """Write as if speaking directly to one person about {topic}. 

This is intimate - you're looking them in the eyes.
- "You" is one person, not an audience
- Say the thing that's hard to say
- Include what you notice about them
- End with what you hope for them

Use ? to ask real questions. Use ... for the unsaid.
Include audio tags like [pause], [tenderly], [softly], [whispers], [sighs] throughout. This should feel like a gift, not a performance.""",

    "eulogy": """Write a piece about {topic} as if it were a eulogy - not for a person, but for a feeling, a time, a way of being.

Structure:
1. "We gather here to remember..."
2. What it meant to us
3. The specific moments we'll miss
4. What it taught us
5. How we carry it forward

Use ... for grief, ? for wondering, ! for celebrating.
Include audio tags like [pause], [softly], [sighs], [sad], [warmly], [hopeful] throughout. Grief and gratitude intertwined.""",

    "manifesto": """Write a passionate manifesto about {topic} in the style of the Great Dictator speech.

Structure:
1. Humble opening ("I don't want to preach...")
2. The problem, stated plainly
3. What we've lost
4. The turn: "But I believe..."
5. Building intensity: "We must..." / "We can..."
6. Rallying cry: "Let us..."

Use ! for rallying cries, ... for dramatic pauses, — for emphasis.
Include audio tags like [softly], [pause], [firmly], [passionately], [shouts], [urgently] throughout. Build from whisper to roar.""",
}


# =============================================================================
# TTS TIMING CONFIGURATION
# =============================================================================
# ElevenLabs TTS speaking rate varies by voice, settings, and content type.
#
# PRODUCTION-TESTED VALUES (from ReWire Journey app):
#   - Journey uses 1.7 words per second (WPS) = 102 WPM
#   - This accounts for [pause] tokens, audio tags, natural pauses, emotional delivery
#   - Tested across 1-minute to 10-minute tracks with consistent results
#
# Why 102 WPM works:
#   - Raw ElevenLabs speech: ~150-165 WPM
#   - After [pause] tokens and audio tags: -15-20% time added
#   - Emotional/dramatic pacing: -10-15% slower
#   - Natural sentence pauses: -5-10% added time
#   - Net effective rate: ~100-105 WPM
#
# SAFETY FACTOR:
#   - Set to 1.0 (100%) - speech fills the ENTIRE music duration
#   - No artificial reduction - user controls timing via Speech Entry slider
#   - If user wants speech to start late, they set Speech Entry > 0
# =============================================================================

DEFAULT_TTS_WPM = 102  # Production-tested: 1.7 words per second

# Safety factor: 1.0 = 100% = no reduction, speech fills entire music duration
# User controls any delay via Speech Entry slider in the UI
DEFAULT_SAFETY_FACTOR = 1.0


# Word count instruction template - STRICT VERSION
WORD_COUNT_INSTRUCTION = """

═══════════════════════════════════════════════════════════════════════════════
CRITICAL WORD COUNT REQUIREMENT - YOU MUST FOLLOW THIS EXACTLY
═══════════════════════════════════════════════════════════════════════════════

TARGET: EXACTLY {target_words} WORDS (absolute maximum: {max_words} words)

This is NON-NEGOTIABLE because:
- The text will be converted to speech and mixed with background music
- If you write too many words, the voice will keep talking after the music ends
- If you write too few words, there will be awkward silence

INSTRUCTIONS:
1. Write your piece with emotional punctuation (?, !, ...) and audio tags ([excited], [whispers], [pause], [sighs])
2. COUNT EVERY WORD (including small words like "a", "the", "is")
3. Audio tags in [square brackets] do NOT count as words (e.g., [pause], [whispers], [excited], [sighs])
4. If you're over {target_words} words, CUT content until you reach the target
5. If you're under, ADD content until you reach the target

TARGET: {target_words} words = approximately {duration_estimate} of speech

BEFORE YOU FINISH: Count your words one more time. You MUST be between {min_words} and {max_words} words.
Audio tags like [pause], [whispers], [excited], [sighs] are FREE - use them generously for emotional delivery!
═══════════════════════════════════════════════════════════════════════════════
"""


def get_system_prompt(style: str = "default") -> str:
    """Get system prompt for a given style."""
    return SYSTEM_PROMPTS.get(style, SYSTEM_PROMPTS["default"])


def get_user_prompt(template: str, topic: str) -> str:
    """Build user prompt from template and topic."""
    template_str = USER_PROMPTS.get(template, USER_PROMPTS["freeform"])
    return template_str.format(topic=topic)


def _format_duration_estimate(target_words: int, words_per_minute: int = DEFAULT_TTS_WPM) -> str:
    """Convert word count to estimated duration string."""
    total_seconds = int((target_words / words_per_minute) * 60)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def build_prompt(
    topic: str,
    style: str = "default",
    template: str = "about_topic",
    custom_system: str = None,
    custom_user: str = None,
    context: str = None,
    target_words: int = None,
) -> tuple[str, str]:
    """
    Build complete prompt pair (system, user) for LLM.
    
    Args:
        topic: The topic to write about
        style: Prompt style (default, chaplin, sagan, etc.)
        template: User prompt template (about_topic, journey, etc.)
        custom_system: Custom system prompt (overrides style)
        custom_user: Custom user prompt (overrides template)
        context: Additional context to add to system prompt
        target_words: Target word count for the generated text
    
    Returns tuple of (system_prompt, user_prompt).
    """
    if custom_system:
        system_prompt = custom_system
        # Add audio tags instruction to custom system prompts too
        if "[excited]" not in system_prompt and "[whispers]" not in system_prompt and "AUDIO TAGS" not in system_prompt:
            system_prompt += AUDIO_TAGS_INSTRUCTION
    else:
        system_prompt = get_system_prompt(style)
    
    if context:
        system_prompt += f"\n\nAdditional context to incorporate:\n{context}"
    
    # Add word count instruction if target_words is specified
    if target_words and target_words > 0:
        duration_estimate = _format_duration_estimate(target_words)
        # Calculate min/max bounds (±5% tolerance, but max is hard limit)
        min_words = int(target_words * 0.95)
        max_words = int(target_words * 1.02)  # Only 2% over allowed
        
        word_count_instruction = WORD_COUNT_INSTRUCTION.format(
            target_words=target_words,
            min_words=min_words,
            max_words=max_words,
            duration_estimate=duration_estimate
        )
        system_prompt += word_count_instruction
    
    if custom_user:
        user_prompt = custom_user
    else:
        user_prompt = get_user_prompt(template, topic)
    
    # Also add word count reminder to user prompt if specified
    if target_words and target_words > 0:
        max_words = int(target_words * 1.02)
        user_prompt += f"\n\n⚠️ WORD COUNT: Write EXACTLY {target_words} words. MAXIMUM allowed: {max_words} words. Count carefully!"
        user_prompt += f"\n💡 EXPRESSION: Use punctuation (?, !, ...) AND audio tags ([excited], [whispers], [pause], [sighs]) freely - tags don't count as words!"
    
    return system_prompt, user_prompt


def calculate_target_words(
    duration_ms: int, 
    words_per_minute: int = DEFAULT_TTS_WPM,
    safety_factor: float = DEFAULT_SAFETY_FACTOR
) -> int:
    """
    Calculate target word count from audio duration.
    
    This applies the safety factor to ensure speech fills the music duration.
    For more precise calculation with voice settings, use calculate_target_words_adjusted().
    
    Args:
        duration_ms: Duration in milliseconds
        words_per_minute: Speaking rate (default DEFAULT_TTS_WPM for emotional narration)
        safety_factor: Multiply result by this (default 1.0 = 100%, no reduction)
    
    Returns:
        Target word count
    """
    duration_seconds = duration_ms / 1000
    duration_minutes = duration_seconds / 60
    raw_words = duration_minutes * words_per_minute
    target_words = int(raw_words * safety_factor)
    return max(10, target_words)  # Minimum 10 words


def calculate_target_words_adjusted(
    duration_ms: int,
    voice_speed: float = 1.0,
    speech_entry_ms: int = 0,
    crossfade_ms: int = 0,
    base_wpm: int = DEFAULT_TTS_WPM,
    safety_factor: float = DEFAULT_SAFETY_FACTOR,
) -> int:
    """
    Calculate target word count with voice speed and timing adjustments.
    
    This provides more accurate word count by accounting for:
    - Voice speed setting (0.5x to 2.0x)
    - Speech entry delay (music plays before voice starts)
    - Crossfade duration (for reference only, not subtracted)
    
    Args:
        duration_ms: Total music duration in milliseconds
        voice_speed: ElevenLabs voice speed multiplier (0.5 to 2.0, default 1.0)
        speech_entry_ms: Delay before voice starts (ms), reduces available time
        crossfade_ms: Crossfade duration at end (ms) - NOT subtracted, handled by mixer
        base_wpm: Base words per minute at speed 1.0 (default 102 WPM)
        safety_factor: Multiply result by this (default 1.0 = 100%, no reduction)
    
    Returns:
        Target word count adjusted for all parameters
    
    Example:
        6 min track (360000ms), speed 1.0x, 3000ms entry:
        - Available time: 360000 - 3000 = 357000ms = 5.95 min
        - Adjusted WPM: 102 * 1.0 = 102
        - Raw words: 5.95 * 102 = 607
        - With safety 1.0: 607 words (fills 100% of available time)
    """
    # Clamp voice_speed to valid range
    voice_speed = max(0.5, min(2.0, voice_speed))
    
    # Calculate effective duration for speech
    # Only subtract speech entry delay (user-controlled via UI slider)
    # Crossfade is handled by the audio mixer, not word count
    effective_duration_ms = duration_ms - speech_entry_ms
    effective_duration_ms = max(0, effective_duration_ms)
    
    # Convert to minutes
    effective_minutes = effective_duration_ms / 60000
    
    # Adjust WPM based on voice speed
    # Lower speed = speech takes longer = fewer words fit in the same time
    # Higher speed = speech is faster = more words fit
    # 
    # If voice_speed is 0.8x, the TTS speaks 20% slower, so:
    #   - Same words take 25% more time (1/0.8 = 1.25)
    #   - To fill the same duration, we need 20% fewer words
    #   - Effective WPM = base_wpm * voice_speed
    adjusted_wpm = base_wpm * voice_speed
    
    # Calculate raw word count
    raw_words = effective_minutes * adjusted_wpm
    
    # Apply safety factor (default 1.0 = no reduction, fills 100%)
    target_words = int(raw_words * safety_factor)
    
    return max(10, target_words)  # Minimum 10 words


def get_default_tts_wpm() -> int:
    """Get the default TTS words per minute value."""
    return DEFAULT_TTS_WPM


def get_default_safety_factor() -> float:
    """Get the default safety factor for word count calculation."""
    return DEFAULT_SAFETY_FACTOR


def list_styles() -> list:
    """List available prompt styles."""
    return [
        {"id": "default", "name": "Default", "description": "Warm, contemplative, universal"},
        {"id": "chaplin", "name": "Chaplin", "description": "Building crescendo from humble to rallying cry"},
        {"id": "sagan", "name": "Sagan", "description": "Cosmic wonder, pale blue dot perspective"},
        {"id": "meditation", "name": "Meditation", "description": "Slow, peaceful, grounding presence"},
        {"id": "gratitude", "name": "Gratitude", "description": "Recognition, connection, quiet warmth"},
        {"id": "wonder", "name": "Wonder", "description": "Ordinary made extraordinary"},
        {"id": "interstellar", "name": "Interstellar", "description": "Love, time, sacrifice, cosmic scale"},
        {"id": "inception", "name": "Inception", "description": "Reality, dreams, ideas that persist"},
    ]


def list_templates() -> list:
    """List available user prompt templates."""
    return [
        {"id": "freeform", "name": "Freeform", "description": "Just the topic, no template"},
        {"id": "about_topic", "name": "About Topic", "description": "Moving piece about [topic]"},
        {"id": "inspired_by", "name": "Inspired By", "description": "Inspired by [idea]"},
        {"id": "journey", "name": "Journey", "description": "Emotional journey through [topic]"},
        {"id": "reflection", "name": "Reflection", "description": "Contemplative reflection"},
        {"id": "letter", "name": "Letter", "description": "Direct, intimate address"},
        {"id": "eulogy", "name": "Eulogy", "description": "Remembrance of [feeling/time/way of being]"},
        {"id": "manifesto", "name": "Manifesto", "description": "Passionate call to action"},
    ]


def get_chaplin_speech() -> str:
    """Get the full Great Dictator speech for reference."""
    return CHAPLIN_SPEECH
