export type Choice = {
  id: string;
  text: string;
  description?: string | null;
};

export type ChapterSummary = {
  number: number;
  title: string;
  filename: string;
  summary?: string | null;
  scene_prompt?: string | null;
  image_prompt?: string | null;
  characters_in_scene: string[];
  choices: Choice[];
  selected_choice_id?: string | null;
  choice_reasoning?: string | null;
  generated_at?: string | null;
  text_model_used?: string | null;
  image_model_used?: string | null;
  scene?: string | null;
  ai_summary?: string | null;
};

export type WorldSummary = {
  title: string;
  slug: string;
  theme: string;
  style_pack: string;
  text_model: string;
  image_model: string;
  maturity_level: string;
  preset: string;
  enable_choices: boolean;
  tick: number;
  chapter_count: number;
  is_current: boolean;
  memory?: string | null;
  authors_note?: string | null;
  world_instructions?: string | null;
};

export type WorldConfig = {
  title: string;
  slug: string;
  theme: string;
  style_pack: string;
  text_model: string;
  image_model: string;
  maturity_level: string;
  preset: string;
  enable_choices: boolean;
  memory?: string | null;
  authors_note?: string | null;
  world_instructions?: string | null;
};

export type WorldDetail = {
  config: WorldConfig;
  state: {
    tick: number;
    next_chapter: number;
    characters: Record<string, { id: string; name: string; description?: string | null }>;
    locations: Record<string, { id: string; name: string; description?: string | null }>;
  };
  chapters: ChapterSummary[];
  is_current: boolean;
};

export type WorldInput = {
  title: string;
  theme: string;
  style_pack: string;
  maturity_level: string;
  preset: string;
  enable_choices: boolean;
  memory?: string;
  authors_note?: string;
  world_instructions?: string;
};

export type SettingsResponse = {
  text_provider: string;
  image_provider: string;
  has_openai_key: boolean;
  has_together_key: boolean;
  has_huggingface_key: boolean;
  has_groq_key: boolean;
  has_openrouter_key: boolean;
  has_gemini_key: boolean;
  has_replicate_token: boolean;
  has_fal_key: boolean;
  global_instructions?: string | null;
  default_style_pack: string;
  default_preset: string;
  default_text_model: string;
  default_image_model: string;
  reader_font_family: string;
  reader_font_size: string;
};

export type SettingsUpdateRequest = {
  text_provider?: string;
  image_provider?: string;
  openai_api_key?: string;
  together_api_key?: string;
  huggingface_api_key?: string;
  groq_api_key?: string;
  openrouter_api_key?: string;
  gemini_api_key?: string;
  replicate_api_token?: string;
  fal_api_key?: string;
  global_instructions?: string;
  default_style_pack?: string;
  default_preset?: string;
  default_text_model?: string;
  default_image_model?: string;
  reader_font_family?: string;
  reader_font_size?: string;
};

export type RandomWorldResponse = {
  title: string;
  theme: string;
  style_pack: string;
  preset: string;
  maturity_level: string;
  memory: string;
};

export type GenerationRequest = {
  no_images: boolean;
  chapter_length: "short" | "medium" | "long";
};

export type JobProgress = {
  stage: "init" | "text" | "post-processing" | "image" | "saving" | "complete" | "error";
  percent: number;
  message: string;
  job_id?: string;
};
