// 화면 문구 4개 언어 (팀 기준 ko·ja·zh·en, 중국어 = 간체)
// 새 문구는 4개 언어를 모두 채운다. 빠지면 한국어로 보인다.
window.I18N = {
  ko: {
    tagline: "피부 고민, 이제 혼자 알아보지 마세요",
    intro: "진료받은 내용을 바탕으로 GlowPass가 복약·관리 방법을 쉽게 알려드려요.",
    choose_lang: "언어 선택", login: "로그인", signup: "회원가입", logout: "로그아웃", withdraw: "회원 탈퇴", withdraw_confirm: "탈퇴하면 진료기록·가이드·병원 요청이 모두 지워지고 되돌릴 수 없어요. 탈퇴할까요?", withdraw_done: "탈퇴가 끝났어요. 챗봇 대화는 30일 안에 자동으로 지워져요.",
    email: "이메일", password: "비밀번호", password_hint: "8자 이상, 대·소문자·숫자·특수문자 포함",
    pw_show: "비밀번호 보기", pw_hide: "비밀번호 숨기기", birth_hint: "숫자만 · 예: 19950505",
    name: "이름", gender: "성별", female: "여성", male: "남성", birth: "생년월일", select_placeholder: "선택하세요", intro_video: "GlowPass 소개 영상",
    phone: "휴대폰 번호", phone_hint: "필수 · 예: 01012345678 또는 +86 138 1234 5678",
    no_account: "계정이 없으신가요?", have_account: "이미 계정이 있으신가요?",
    home_title: "내 피부 관리", my_records: "내 진료기록", no_records: "아직 진료기록이 없어요.",
    add_record: "진료기록 입력하기", make_guide: "AI 가이드 만들기", my_guides: "내 AI 가이드",
    visit_date: "진료일", hospital: "병원 이름", procedure: "진료/시술 내용", procedure_ph: "예: 여드름 치료, 레이저 토닝",
    doctor_note: "의사 설명 메모", drugs: "처방약", drug_name: "약 이름", dose: "1회 용량", dose_ph: "예: 1정",
    times_per_day: "하루 횟수", days: "며칠분", add_drug: "+ 약 추가", save: "저장하고 AI 가이드 만들기",
    ocr_upload: "처방전 사진으로 입력",
    analyzing: "AI 분석 · 가이드 생성", step_record: "진료기록·처방정보 확인", step_rag: "근거 자료 검색 (FR-02)",
    step_guide: "AI 복약·생활관리 가이드 생성 (FR-03)", wait_msg: "조금만 기다려주세요. 다 되면 바로 보여드릴게요.",
    guide_title: "AI 맞춤 가이드", tab_med: "복약 안내", tab_life: "생활관리", tab_src: "출처",
    prescriptions_title: "처방 내용", prescriptions_note: "병원에서 받은 처방을 입력하신 그대로 보여드려요. 복용 방법은 처방을 따르세요.",
    no_source: "이 기록과 관련된 검증된 자료가 아직 없어 가이드를 만들지 않았어요. 담당 의료진에게 문의해 주세요.",
    failed: "가이드를 만들지 못했어요. 잠시 후 다시 시도해 주세요.", empty_section: "이 항목은 근거 자료가 없어요.",
    ask_ai: "AI에게 더 물어보기", contact_hospital: "담당 병원 문의", coming_soon: "곧 연결돼요",
    times_unit: "하루 {n}회", days_unit: "{n}일분", relevance: "관련도", open_source: "원문 보기",
    disclaimer_short: "※ 제공 정보는 참고용이며 의학적 판단·처방을 대체하지 않아요.",
    back: "← 뒤로", status_PENDING: "생성 중", status_DONE: "완료", status_NO_SOURCE: "자료 없음", status_FAILED: "실패",
    err_login: "이메일 또는 비밀번호를 확인해 주세요.", err_generic: "요청을 처리하지 못했어요.", signup_done: "가입이 완료됐어요. 로그인해 주세요.",
  },
  ja: {
    tagline: "肌の悩み、もう一人で調べなくて大丈夫",
    intro: "受診内容をもとに、GlowPassがお薬とケアの方法をわかりやすくお伝えします。",
    choose_lang: "言語を選択", login: "ログイン", signup: "新規登録", logout: "ログアウト", withdraw: "退会", withdraw_confirm: "退会すると診療記録・ガイド・病院への依頼がすべて削除され、元に戻せません。退会しますか？", withdraw_done: "退会しました。チャットの会話は30日以内に自動で削除されます。",
    email: "メールアドレス", password: "パスワード", password_hint: "8文字以上・大文字・小文字・数字・記号を含む",
    pw_show: "パスワードを表示", pw_hide: "パスワードを隠す", birth_hint: "数字のみ・例: 19950505",
    name: "お名前", gender: "性別", female: "女性", male: "男性", birth: "生年月日", select_placeholder: "選択してください", intro_video: "GlowPass 紹介動画",
    phone: "携帯電話番号", phone_hint: "必須 · 例: +81 90 1234 5678",
    no_account: "アカウントをお持ちでないですか？", have_account: "すでにアカウントをお持ちですか？",
    home_title: "わたしの肌ケア", my_records: "診療記録", no_records: "まだ診療記録がありません。",
    add_record: "診療記録を入力", make_guide: "AIガイドを作る", my_guides: "AIガイド",
    visit_date: "受診日", hospital: "病院名", procedure: "診療・施術内容", procedure_ph: "例: ニキビ治療、レーザートーニング",
    doctor_note: "医師の説明メモ", drugs: "処方薬", drug_name: "薬の名前", dose: "1回量", dose_ph: "例: 1錠",
    times_per_day: "1日の回数", days: "日数", add_drug: "+ 薬を追加", save: "保存してAIガイドを作る",
    ocr_upload: "処方箋の写真で入力",
    analyzing: "AI分析・ガイド作成", step_record: "診療記録・処方情報の確認", step_rag: "根拠資料の検索 (FR-02)",
    step_guide: "AIお薬・生活ケアガイドの作成 (FR-03)", wait_msg: "少々お待ちください。できたらすぐにお見せします。",
    guide_title: "AIガイド", tab_med: "お薬の案内", tab_life: "生活ケア", tab_src: "出典",
    prescriptions_title: "処方内容", prescriptions_note: "病院で受けた処方を入力どおりに表示しています。飲み方は処方に従ってください。",
    no_source: "この記録に関する確認済みの資料がまだないため、ガイドを作成しませんでした。担当医にご相談ください。",
    failed: "ガイドを作成できませんでした。しばらくしてからもう一度お試しください。", empty_section: "この項目の根拠資料はありません。",
    ask_ai: "AIにもっと聞く", contact_hospital: "担当病院に問い合わせ", coming_soon: "まもなく接続されます",
    times_unit: "1日{n}回", days_unit: "{n}日分", relevance: "関連度", open_source: "原文を見る",
    disclaimer_short: "※ 提供情報は参考用であり、医学的な判断や処方に代わるものではありません。",
    back: "← 戻る", status_PENDING: "作成中", status_DONE: "完了", status_NO_SOURCE: "資料なし", status_FAILED: "失敗",
    err_login: "メールアドレスまたはパスワードを確認してください。", err_generic: "リクエストを処理できませんでした。", signup_done: "登録が完了しました。ログインしてください。",
  },
  zh: {
    tagline: "皮肤烦恼，不用再一个人查资料",
    intro: "GlowPass 根据您的就诊内容，用简单的方式告诉您用药和护理方法。",
    choose_lang: "选择语言", login: "登录", signup: "注册", logout: "退出", withdraw: "注销账号", withdraw_confirm: "注销后，诊疗记录、指南和医院请求将全部删除且无法恢复。确定注销吗？", withdraw_done: "账号已注销。聊天记录将在30天内自动删除。",
    email: "邮箱", password: "密码", password_hint: "至少8位，包含大小写字母、数字和符号",
    pw_show: "显示密码", pw_hide: "隐藏密码", birth_hint: "仅数字 · 例: 19950505",
    name: "姓名", gender: "性别", female: "女", male: "男", birth: "出生日期", select_placeholder: "请选择", intro_video: "GlowPass 介绍视频",
    phone: "手机号码", phone_hint: "必填 · 例如: +86 138 1234 5678",
    no_account: "还没有账号？", have_account: "已有账号？",
    home_title: "我的皮肤管理", my_records: "我的就诊记录", no_records: "还没有就诊记录。",
    add_record: "填写就诊记录", make_guide: "生成 AI 指南", my_guides: "我的 AI 指南",
    visit_date: "就诊日期", hospital: "医院名称", procedure: "诊疗/项目内容", procedure_ph: "例如: 痘痘治疗、激光美白",
    doctor_note: "医生说明备注", drugs: "处方药", drug_name: "药名", dose: "每次用量", dose_ph: "例如: 1片",
    times_per_day: "每天次数", days: "天数", add_drug: "+ 添加药品", save: "保存并生成 AI 指南",
    ocr_upload: "用处方照片填写",
    analyzing: "AI 分析 · 生成指南", step_record: "确认就诊记录和处方信息", step_rag: "检索依据资料 (FR-02)",
    step_guide: "生成 AI 用药·生活护理指南 (FR-03)", wait_msg: "请稍等，完成后马上为您显示。",
    guide_title: "AI 专属指南", tab_med: "用药说明", tab_life: "生活护理", tab_src: "出处",
    prescriptions_title: "处方内容", prescriptions_note: "按您填写的内容显示医院开具的处方。请按处方用药。",
    no_source: "暂时没有与此记录相关的已核实资料，因此未生成指南。请咨询主治医生。",
    failed: "未能生成指南，请稍后再试。", empty_section: "此项没有依据资料。",
    ask_ai: "继续问 AI", contact_hospital: "联系就诊医院", coming_soon: "即将开通",
    times_unit: "每天{n}次", days_unit: "{n}天量", relevance: "相关度", open_source: "查看原文",
    disclaimer_short: "※ 所提供信息仅供参考，不能代替医学判断或处方。",
    back: "← 返回", status_PENDING: "生成中", status_DONE: "完成", status_NO_SOURCE: "无资料", status_FAILED: "失败",
    err_login: "请检查邮箱或密码。", err_generic: "请求未能完成。", signup_done: "注册完成，请登录。",
  },
  en: {
    tagline: "No more figuring out your skin care alone",
    intro: "GlowPass explains your medicines and after-care simply, based on your clinic visit.",
    choose_lang: "Choose language", login: "Log in", signup: "Sign up", logout: "Log out", withdraw: "Delete account", withdraw_confirm: "Deleting your account permanently removes your records, guides and clinic requests. This cannot be undone. Delete?", withdraw_done: "Your account was deleted. Chat history is removed automatically within 30 days.",
    email: "Email", password: "Password", password_hint: "8+ characters with upper, lower, number and symbol",
    pw_show: "Show password", pw_hide: "Hide password", birth_hint: "Numbers only · e.g. 19950505",
    name: "Name", gender: "Gender", female: "Female", male: "Male", birth: "Date of birth", select_placeholder: "Select", intro_video: "GlowPass intro video",
    phone: "Mobile number", phone_hint: "Required · e.g. +1 415 555 0100",
    no_account: "No account yet?", have_account: "Already have an account?",
    home_title: "My skin care", my_records: "My clinic records", no_records: "No clinic records yet.",
    add_record: "Add a clinic record", make_guide: "Create AI guide", my_guides: "My AI guides",
    visit_date: "Visit date", hospital: "Clinic name", procedure: "Treatment / procedure", procedure_ph: "e.g. acne care, laser toning",
    doctor_note: "Doctor's notes", drugs: "Prescribed medicines", drug_name: "Medicine name", dose: "Dose", dose_ph: "e.g. 1 tablet",
    times_per_day: "Times a day", days: "Days", add_drug: "+ Add medicine", save: "Save and create AI guide",
    ocr_upload: "Fill in from a prescription photo",
    analyzing: "AI analysis · creating guide", step_record: "Checking your records and prescriptions", step_rag: "Searching trusted sources (FR-02)",
    step_guide: "Writing your medicine and care guide (FR-03)", wait_msg: "Please wait a moment. We'll show it as soon as it's ready.",
    guide_title: "Your AI guide", tab_med: "Medicines", tab_life: "Daily care", tab_src: "Sources",
    prescriptions_title: "Your prescription", prescriptions_note: "Shown exactly as you entered it from the clinic. Follow your prescription.",
    no_source: "We don't have verified sources for this record yet, so no guide was created. Please ask your doctor.",
    failed: "We couldn't create the guide. Please try again later.", empty_section: "No sources for this part.",
    ask_ai: "Ask AI more", contact_hospital: "Contact your clinic", coming_soon: "Coming soon",
    times_unit: "{n} times a day", days_unit: "{n} days", relevance: "Relevance", open_source: "Open source",
    disclaimer_short: "※ This information is for reference and does not replace medical judgement or prescriptions.",
    back: "← Back", status_PENDING: "Creating", status_DONE: "Done", status_NO_SOURCE: "No sources", status_FAILED: "Failed",
    err_login: "Please check your email or password.", err_generic: "We couldn't process the request.", signup_done: "Signed up. Please log in.",
  },
};

// 챗봇 (FR-04) 문구
Object.assign(window.I18N.ko, {
  chat_open: "AI 챗봇에게 물어보기", chat_title: "AI 상담 챗봇",
  chat_intro: "GlowPass 안내 자료를 바탕으로 일반적인 정보만 안내해요. 내 몸에 맞는지는 꼭 의료진과 상담하세요.",
  chat_ph: "궁금한 점을 입력하세요 (Enter = 보내기)", send: "보내기", chat_new: "새 대화 시작",
  chat_error: "답을 받지 못했어요. 잠시 후 다시 시도해 주세요.", chat_sources: "근거:",
  emergency_title: "⚠ 응급일 수 있어요", emergency_body: "말씀하신 증상은 바로 진료가 필요할 수 있어요. 지금 119에 전화하거나 가까운 응급실로 가세요.",
  call_119: "119 전화하기", find_er: "가까운 응급실 찾기", call_1330: "외국어 관광안내 1330 전화",
});
Object.assign(window.I18N.ja, {
  chat_open: "AIチャットボットに質問", chat_title: "AI相談チャットボット",
  chat_intro: "GlowPassの案内資料をもとに一般的な情報のみご案内します。ご自身に合うかは必ず医療スタッフにご相談ください。",
  chat_ph: "質問を入力してください（Enterで送信）", send: "送信", chat_new: "新しい会話",
  chat_error: "回答を受け取れませんでした。しばらくしてからもう一度お試しください。", chat_sources: "根拠:",
  emergency_title: "⚠ 緊急の可能性があります", emergency_body: "その症状はすぐに診察が必要な場合があります。今すぐ119に電話するか、近くの救急外来へ行ってください。",
  call_119: "119に電話する", find_er: "近くの救急外来を探す", call_1330: "多言語観光案内 1330 に電話",
});
Object.assign(window.I18N.zh, {
  chat_open: "向AI聊天机器人提问", chat_title: "AI咨询聊天机器人",
  chat_intro: "仅根据GlowPass的说明资料提供一般性信息。是否适合您，请务必咨询医护人员。",
  chat_ph: "请输入您的问题（按Enter发送）", send: "发送", chat_new: "开始新对话",
  chat_error: "未能获得回答，请稍后再试。", chat_sources: "依据：",
  emergency_title: "⚠ 可能是紧急情况", emergency_body: "您描述的症状可能需要立即就医。请立即拨打119或前往最近的急诊室。",
  call_119: "拨打119", find_er: "查找附近的急诊室", call_1330: "拨打多语种旅游热线 1330",
});
Object.assign(window.I18N.en, {
  chat_open: "Ask the AI chatbot", chat_title: "AI Chatbot",
  chat_intro: "General information only, based on our reference documents. Always ask your medical team whether it applies to you.",
  chat_ph: "Type your question (Enter to send)", send: "Send", chat_new: "New conversation",
  chat_error: "We couldn't get an answer. Please try again shortly.", chat_sources: "Sources:",
  emergency_title: "⚠ This may be an emergency", emergency_body: "The symptoms you describe may need immediate care. Call 119 now or go to the nearest emergency room.",
  call_119: "Call 119", find_er: "Find the nearest ER", call_1330: "Call 1330 (multilingual travel hotline)",
});

// 처방전 사진 인식 (FR-05) 문구
Object.assign(window.I18N.ko, {
  ocr_upload: "처방전·약봉투 사진으로 입력", ocr_hint: "이름·주민등록번호는 가리고 찍어 주세요. 글자 인식을 위해 사진이 외부 AI 서비스로 전송될 수 있고, 사진 자체는 저장하지 않아요.",
  ocr_reading: "사진을 읽고 있어요…", ocr_done: "사진에서 읽은 내용으로 채웠어요.",
  ocr_check: "글자를 잘못 읽을 수 있어요. 처방전과 한 번 더 비교해 고친 뒤 저장해 주세요.",
  ocr_items_not_read: "약 목록은 읽지 못했어요. 직접 입력해 주세요.", ocr_fake: "(데모용 가짜 인식 결과)",
  ocr_failed: "사진을 읽지 못했어요. 밝고 선명하게 다시 찍거나 직접 입력해 주세요.", ocr_badge: "사진 입력",
});
Object.assign(window.I18N.ja, {
  ocr_upload: "処方箋・薬袋の写真で入力", ocr_hint: "氏名・個人番号は隠して撮影してください。文字認識のため写真が外部AIサービスに送信される場合があり、写真自体は保存しません。",
  ocr_reading: "写真を読み取っています…", ocr_done: "写真から読み取った内容で入力しました。",
  ocr_check: "文字を読み間違えることがあります。処方箋と見比べて修正してから保存してください。",
  ocr_items_not_read: "お薬の一覧は読み取れませんでした。直接入力してください。", ocr_fake: "（デモ用の仮の読み取り結果）",
  ocr_failed: "写真を読み取れませんでした。明るく鮮明に撮り直すか、直接入力してください。", ocr_badge: "写真入力",
});
Object.assign(window.I18N.zh, {
  ocr_upload: "拍摄处方或药袋自动填写", ocr_hint: "请遮住姓名和身份证号后拍摄。为识别文字，照片可能会发送至外部AI服务；照片本身不会保存。",
  ocr_reading: "正在识别照片…", ocr_done: "已根据照片识别内容填写。",
  ocr_check: "识别可能有误。请与处方核对并修改后再保存。",
  ocr_items_not_read: "未能识别药品列表，请手动填写。", ocr_fake: "（演示用的模拟识别结果）",
  ocr_failed: "未能识别照片。请在光线充足处清晰重拍，或手动填写。", ocr_badge: "照片录入",
});
Object.assign(window.I18N.en, {
  ocr_upload: "Fill in from a prescription photo", ocr_hint: "Cover your name and ID number before taking the photo. The photo may be sent to an external AI service to read the text; the photo itself is not stored.",
  ocr_reading: "Reading the photo…", ocr_done: "Filled in from the photo.",
  ocr_check: "The text may be misread. Compare with your prescription and fix it before saving.",
  ocr_items_not_read: "We couldn't read the medicine list. Please enter it yourself.", ocr_fake: "(Demo: simulated result)",
  ocr_failed: "We couldn't read the photo. Retake it bright and sharp, or enter the details yourself.", ocr_badge: "From photo",
});

// 외국인 가입 문구
Object.assign(window.I18N.ko, { nationality: "국적", nat_cn: "중국", nat_jp: "일본", nat_us: "미국", nat_kr: "한국", nat_other: "기타" });
Object.assign(window.I18N.ja, { nationality: "国籍", nat_cn: "中国", nat_jp: "日本", nat_us: "アメリカ", nat_kr: "韓国", nat_other: "その他" });
Object.assign(window.I18N.zh, { nationality: "国籍", nat_cn: "中国", nat_jp: "日本", nat_us: "美国", nat_kr: "韩国", nat_other: "其他" });
Object.assign(window.I18N.en, { nationality: "Nationality", nat_cn: "China", nat_jp: "Japan", nat_us: "USA", nat_kr: "Korea", nat_other: "Other" });

// 👍/👎 피드백 문구
Object.assign(window.I18N.ko, { fb_question: "도움이 됐나요?", fb_thanks: "의견 고마워요!", fb_wrong_info: "내용이 틀린 것 같아요",
  fb_hard_to_understand: "이해하기 어려워요", fb_not_relevant: "내 상황과 관계없어요", fb_other: "기타" });
Object.assign(window.I18N.ja, { fb_question: "役に立ちましたか？", fb_thanks: "ご意見ありがとうございます！", fb_wrong_info: "内容が間違っていそう",
  fb_hard_to_understand: "わかりにくい", fb_not_relevant: "自分の状況と関係ない", fb_other: "その他" });
Object.assign(window.I18N.zh, { fb_question: "对您有帮助吗？", fb_thanks: "感谢您的反馈！", fb_wrong_info: "内容似乎有误",
  fb_hard_to_understand: "难以理解", fb_not_relevant: "与我的情况无关", fb_other: "其他" });
Object.assign(window.I18N.en, { fb_question: "Was this helpful?", fb_thanks: "Thanks for the feedback!", fb_wrong_info: "Seems incorrect",
  fb_hard_to_understand: "Hard to understand", fb_not_relevant: "Not relevant to me", fb_other: "Other" });

// 서버 에러 (상태코드별) — 한국어는 서버 문구를 그대로 보여준다
Object.assign(window.I18N.ko, { err_exists: "이미 사용 중이에요.", err_too_big: "파일이 너무 커요.", err_file_type: "JPG·PNG 사진만 올릴 수 있어요.",
  err_input: "입력한 내용을 확인해 주세요.", err_limit: "오늘 사용할 수 있는 횟수를 모두 썼어요." });
Object.assign(window.I18N.ja, { err_exists: "メールアドレス・電話番号がすでに使われているか、すでに保存済みです。", err_too_big: "ファイルが大きすぎます（5MBまで）。",
  err_file_type: "JPG・PNGの写真のみアップロードできます。", err_input: "入力内容を確認してください（パスワードは大文字・小文字・数字・記号を含む8文字以上）。",
  err_limit: "本日の利用回数の上限に達しました。" });
Object.assign(window.I18N.zh, { err_exists: "邮箱或手机号已被使用，或该内容已保存。", err_too_big: "文件太大（最大5MB）。",
  err_file_type: "只能上传JPG或PNG照片。", err_input: "请检查填写内容（密码需8位以上，包含大写、小写字母、数字和符号）。",
  err_limit: "今日使用次数已达上限。" });
Object.assign(window.I18N.en, { err_exists: "This email or phone number is already in use, or it was already saved.", err_too_big: "The file is too large (max 5MB).",
  err_file_type: "Only JPG or PNG photos can be uploaded.", err_input: "Please check your input (password: 8+ characters with upper, lower, number and symbol).",
  err_limit: "You've reached today's limit." });

// 챗봇이 참고하는 내 기록
Object.assign(window.I18N.ko, { chat_context: "최근 진료기록 참고 (약 이름이 AI 답변에 쓰여요):" });
Object.assign(window.I18N.ja, { chat_context: "最近の診療記録を参照:" });
Object.assign(window.I18N.zh, { chat_context: "参考最近的就诊记录：" });
Object.assign(window.I18N.en, { chat_context: "Using your latest record:" });

// 병원 문의 카드
Object.assign(window.I18N.ko, { card_symptoms: "지금 어떤 증상이 있나요?", card_urgent: "이런 증상은 바로 응급", card_since: "언제부터",
  card_pick: "증상을 고르면 병원에 보여줄 문장이 만들어져요.", card_show_staff: "병원 직원에게 보여주거나 메시지로 보내세요",
  card_copy: "문장 복사하기", card_copied: "복사했어요", card_copy_fail: "복사하지 못했어요. 길게 눌러 복사해 주세요.",
  card_my_lang: "내 언어로 내용 보기", card_note: "증상을 정리한 문장일 뿐 진단이 아니에요. 진료가 필요한지는 병원이 판단해요." });
Object.assign(window.I18N.ja, { card_symptoms: "今どんな症状がありますか？", card_urgent: "これらはすぐに救急へ", card_since: "いつから",
  card_pick: "症状を選ぶと、病院に見せる韓国語の文が作られます。", card_show_staff: "病院のスタッフに見せるか、メッセージで送ってください",
  card_copy: "文をコピー", card_copied: "コピーしました", card_copy_fail: "コピーできませんでした。長押ししてコピーしてください。",
  card_my_lang: "日本語で内容を見る", card_note: "症状をまとめた文で、診断ではありません。受診が必要かは病院が判断します。" });
Object.assign(window.I18N.zh, { card_symptoms: "现在有什么症状？", card_urgent: "以下症状请立即急救", card_since: "从什么时候开始",
  card_pick: "选择症状后，会生成给医院看的韩语句子。", card_show_staff: "请出示给医院工作人员，或通过消息发送",
  card_copy: "复制句子", card_copied: "已复制", card_copy_fail: "复制失败，请长按复制。",
  card_my_lang: "用中文查看内容", card_note: "这只是整理症状的句子，不是诊断。是否需要就诊由医院判断。" });
Object.assign(window.I18N.en, { card_symptoms: "What symptoms do you have now?", card_urgent: "These need emergency care now", card_since: "Since when",
  card_pick: "Pick your symptoms to create a Korean message for the clinic.", card_show_staff: "Show this to clinic staff or send it as a message",
  card_copy: "Copy message", card_copied: "Copied", card_copy_fail: "Couldn't copy. Press and hold to copy.",
  card_my_lang: "See it in English", card_note: "This only describes your symptoms; it is not a diagnosis. The clinic decides whether you need care." });

// 배포 전 리뷰 반영 문구
Object.assign(window.I18N.ko, {
  messenger: "연락용 메신저", messenger_id: "메신저 아이디", messenger_id_hint: "예: wxid_abc123",
  still_pending: "아직 가이드를 만들고 있어요. 잠시 뒤 '내 AI 가이드' 에서 다시 확인해 주세요.",
  record_changed: "가이드를 만든 뒤 진료기록이 바뀌었어요. 처방 칸은 지금 기록, 안내 글은 예전 기록 기준이에요.",
  remake_guide: "가이드 다시 만들기", record_saved_guide_failed: "진료기록은 저장됐어요. 가이드는 만들지 못했어요.",
});
Object.assign(window.I18N.ja, {
  messenger: "連絡用メッセンジャー", messenger_id: "メッセンジャーID", messenger_id_hint: "例: line_abc123",
  still_pending: "まだガイドを作成中です。しばらくしてから「AIガイド」で確認してください。",
  record_changed: "ガイド作成後に診療記録が変更されました。処方欄は現在の記録、案内文は以前の記録に基づいています。",
  remake_guide: "ガイドを作り直す", record_saved_guide_failed: "診療記録は保存されました。ガイドは作成できませんでした。",
});
Object.assign(window.I18N.zh, {
  messenger: "联系用通讯软件", messenger_id: "通讯软件账号", messenger_id_hint: "例如：wxid_abc123",
  still_pending: "指南仍在生成中，请稍后在“我的 AI 指南”中查看。",
  record_changed: "生成指南后就诊记录已更改。处方栏为当前记录，说明文字基于之前的记录。",
  remake_guide: "重新生成指南", record_saved_guide_failed: "就诊记录已保存，但未能生成指南。",
});
Object.assign(window.I18N.en, {
  messenger: "Messenger for contact", messenger_id: "Messenger ID", messenger_id_hint: "e.g. +14155550123",
  still_pending: "Your guide is still being created. Please check 'My AI guides' again shortly.",
  record_changed: "Your record changed after this guide was made. Prescriptions show the current record; the guide text is based on the old one.",
  remake_guide: "Make the guide again", record_saved_guide_failed: "Your record was saved, but the guide couldn't be created.",
});

// 병원 찾기
Object.assign(window.I18N.ko, { hosp_title: "병원 찾기", hosp_region: "지역", hosp_dept: "진료과", hosp_all_regions: "전체 지역", hosp_all_depts: "전체",
  hosp_gangnam: "강남구", hosp_seocho: "서초구", hosp_junggu: "중구(명동)", hosp_mapo: "마포구", hosp_songpa: "송파구", hosp_busan: "부산",
  hosp_derm: "피부과", hosp_plastic: "성형외과", hosp_only_my_lang: "내 언어로 상담 가능한 곳만", hosp_none: "조건에 맞는 병원이 없어요.",
  hosp_count: "{n}곳 (이름 순)", hosp_principle: "GlowPass 는 병원을 추천하거나 순위를 매기지 않아요. 목록을 보고 직접 선택하세요. 병원 연결 수수료도 받지 않아요.",
  hosp_demo_note: "※ 지금 목록은 데모용 가짜 병원이에요. 실제 공공데이터로 바꿀 예정이에요." });
Object.assign(window.I18N.ja, { hosp_title: "病院を探す", hosp_region: "地域", hosp_dept: "診療科", hosp_all_regions: "すべての地域", hosp_all_depts: "すべて",
  hosp_gangnam: "江南区", hosp_seocho: "瑞草区", hosp_junggu: "中区（明洞）", hosp_mapo: "麻浦区", hosp_songpa: "松坡区", hosp_busan: "釜山",
  hosp_derm: "皮膚科", hosp_plastic: "形成外科", hosp_only_my_lang: "日本語で相談できる病院のみ", hosp_none: "条件に合う病院がありません。",
  hosp_count: "{n}件（名前順）", hosp_principle: "GlowPassは病院を推薦したり順位を付けたりしません。一覧を見てご自身で選んでください。紹介手数料も受け取りません。",
  hosp_demo_note: "※ 現在の一覧はデモ用の架空の病院です。実際の公共データに置き換える予定です。" });
Object.assign(window.I18N.zh, { hosp_title: "查找医院", hosp_region: "地区", hosp_dept: "科室", hosp_all_regions: "全部地区", hosp_all_depts: "全部",
  hosp_gangnam: "江南区", hosp_seocho: "瑞草区", hosp_junggu: "中区（明洞）", hosp_mapo: "麻浦区", hosp_songpa: "松坡区", hosp_busan: "釜山",
  hosp_derm: "皮肤科", hosp_plastic: "整形外科", hosp_only_my_lang: "只看可用中文咨询的医院", hosp_none: "没有符合条件的医院。",
  hosp_count: "{n}家（按名称排序）", hosp_principle: "GlowPass不推荐医院，也不进行排名。请查看列表自行选择。我们也不收取任何转介费用。",
  hosp_demo_note: "※ 当前列表为演示用的虚拟医院，之后将替换为真实的公共数据。" });
Object.assign(window.I18N.en, { hosp_title: "Find a clinic", hosp_region: "Area", hosp_dept: "Department", hosp_all_regions: "All areas", hosp_all_depts: "All",
  hosp_gangnam: "Gangnam-gu", hosp_seocho: "Seocho-gu", hosp_junggu: "Jung-gu (Myeongdong)", hosp_mapo: "Mapo-gu", hosp_songpa: "Songpa-gu", hosp_busan: "Busan",
  hosp_derm: "Dermatology", hosp_plastic: "Plastic surgery", hosp_only_my_lang: "Only clinics that speak English", hosp_none: "No clinics match.",
  hosp_count: "{n} clinics (by name)", hosp_principle: "GlowPass does not recommend or rank clinics. Look at the list and choose yourself. We take no referral fees.",
  hosp_demo_note: "※ This list shows fictional demo clinics. It will be replaced with real public data." });

// 데모 운영 표시 — 의료진 감수 전 안내문을 근거로 쓰는 중
Object.assign(window.I18N.ko, { demo_banner: "데모 버전이에요. AI 답변의 근거 자료는 아직 의료진 감수 전이에요. 실제 치료 판단은 꼭 의료진과 상담하세요.", unreviewed_badge: "감수 전 자료" });
Object.assign(window.I18N.ja, { demo_banner: "デモ版です。AI回答の根拠資料はまだ医療者の監修前です。実際の治療の判断は必ず医療者にご相談ください。", unreviewed_badge: "監修前の資料" });
Object.assign(window.I18N.zh, { demo_banner: "这是演示版。AI回答所依据的资料尚未经过医务人员审核。实际治疗请务必咨询医务人员。", unreviewed_badge: "未经审核的资料" });
Object.assign(window.I18N.en, { demo_banner: "This is a demo. The sources behind AI answers have not yet been reviewed by medical staff. Always consult a medical professional about your treatment.", unreviewed_badge: "Not yet reviewed" });

// 병원 연락 요청 (API 명세서 23·24번)
Object.assign(window.I18N.ko, { hc_request: "연락 요청", hc_request_from_card: "병원 목록에서 연락 요청하기", hc_method: "연락 받을 방법",
  hc_m_messenger: "메신저 (가입 때 적은 계정)", hc_m_phone: "전화", hc_m_email: "이메일", hc_m_visit: "방문 안내", hc_memo: "병원에 남길 말 (선택)",
  hc_send: "요청 보내기", hc_sent: "요청을 보냈어요. 병원이 확인하면 상태가 바뀌어요.", hc_mine: "내 연락 요청", hc_none: "아직 보낸 요청이 없어요.",
  hc_cancel: "요청 취소", hc_status_requested: "접수됨", hc_status_in_progress: "병원 확인 중", hc_status_completed: "연락 완료", hc_status_cancelled: "취소됨",
  hc_login_needed: "연락 요청은 로그인 후 할 수 있어요.", hc_about_record: "고른 병원에 내 시술 기록에 대한 문의로 보냅니다.",
  hc_demo: "※ 데모 버전에서는 실제 병원에 전달되지 않아요." });
Object.assign(window.I18N.ja, { hc_request: "連絡をリクエスト", hc_request_from_card: "病院一覧から連絡をリクエスト", hc_method: "連絡の受け方",
  hc_m_messenger: "メッセンジャー（登録したアカウント）", hc_m_phone: "電話", hc_m_email: "メール", hc_m_visit: "来院のご案内", hc_memo: "病院へのメッセージ（任意）",
  hc_send: "リクエストを送る", hc_sent: "リクエストを送りました。病院が確認すると状態が変わります。", hc_mine: "連絡リクエスト一覧", hc_none: "まだリクエストはありません。",
  hc_cancel: "取り消す", hc_status_requested: "受付済み", hc_status_in_progress: "病院が確認中", hc_status_completed: "連絡済み", hc_status_cancelled: "取り消し",
  hc_login_needed: "連絡リクエストはログイン後に利用できます。", hc_about_record: "選んだ病院に、施術記録についての問い合わせとして送ります。",
  hc_demo: "※ デモ版では実際の病院には届きません。" });
Object.assign(window.I18N.zh, { hc_request: "请求联系", hc_request_from_card: "从医院列表请求联系", hc_method: "希望的联系方式",
  hc_m_messenger: "即时通讯（注册时填写的账号）", hc_m_phone: "电话", hc_m_email: "邮件", hc_m_visit: "到院说明", hc_memo: "给医院的留言（可选）",
  hc_send: "发送请求", hc_sent: "请求已发送。医院确认后状态会更新。", hc_mine: "我的联系请求", hc_none: "还没有发送过请求。",
  hc_cancel: "取消请求", hc_status_requested: "已受理", hc_status_in_progress: "医院确认中", hc_status_completed: "已联系", hc_status_cancelled: "已取消",
  hc_login_needed: "登录后才能请求联系。", hc_about_record: "将作为关于您治疗记录的咨询发送给所选医院。",
  hc_demo: "※ 演示版不会真正发送给医院。" });
Object.assign(window.I18N.en, { hc_request: "Request contact", hc_request_from_card: "Request contact from the clinic list", hc_method: "How should they contact you?",
  hc_m_messenger: "Messenger (account from sign-up)", hc_m_phone: "Phone", hc_m_email: "Email", hc_m_visit: "Visit information", hc_memo: "Message to the clinic (optional)",
  hc_send: "Send request", hc_sent: "Request sent. The status changes when the clinic checks it.", hc_mine: "My contact requests", hc_none: "No requests yet.",
  hc_cancel: "Cancel request", hc_status_requested: "Received", hc_status_in_progress: "Clinic checking", hc_status_completed: "Contacted", hc_status_cancelled: "Cancelled",
  hc_login_needed: "Log in to request contact.", hc_about_record: "This is sent to the clinic you choose as a question about your treatment record.",
  hc_demo: "※ In the demo, requests are not delivered to real clinics." });
Object.assign(window.I18N.ko, { hc_after_emergency: "시술 병원에도 알리기 (연락 요청)" });
Object.assign(window.I18N.ja, { hc_after_emergency: "施術した病院にも知らせる（連絡リクエスト）" });
Object.assign(window.I18N.zh, { hc_after_emergency: "同时通知做治疗的医院（请求联系）" });
Object.assign(window.I18N.en, { hc_after_emergency: "Also tell your clinic (request contact)" });
Object.assign(window.I18N.ko, { hc_about_alert: "위험 신호 안내에서 왔어요. 증상이 심하면 병원 연락을 기다리지 말고 119에 먼저 전화하세요." });
Object.assign(window.I18N.ja, { hc_about_alert: "危険サインの案内から来ました。症状が重い場合は病院の連絡を待たずに、まず119に電話してください。" });
Object.assign(window.I18N.zh, { hc_about_alert: "您是从危险信号提示进入的。症状严重时请不要等待医院联系，先拨打119。" });
Object.assign(window.I18N.en, { hc_about_alert: "You came from a warning-sign alert. If symptoms are severe, call 119 first instead of waiting for the clinic." });

// 가이드 음성·카드 (선택기능 FR-08)
Object.assign(window.I18N.ko, { tts_play: "🔊 음성으로 듣기", tts_stop: "⏹ 멈추기", tts_unsupported: "이 브라우저는 음성 읽기를 지원하지 않아요.", card_save: "🖼 카드 이미지로 저장" });
Object.assign(window.I18N.ja, { tts_play: "🔊 音声で聞く", tts_stop: "⏹ 停止", tts_unsupported: "このブラウザは音声読み上げに対応していません。", card_save: "🖼 カード画像で保存" });
Object.assign(window.I18N.zh, { tts_play: "🔊 语音朗读", tts_stop: "⏹ 停止", tts_unsupported: "此浏览器不支持语音朗读。", card_save: "🖼 保存为卡片图片" });
Object.assign(window.I18N.en, { tts_play: "🔊 Listen", tts_stop: "⏹ Stop", tts_unsupported: "This browser can't read text aloud.", card_save: "🖼 Save as card image" });

// 복약·가이드 확인 알림 (선택기능 FR-10)
Object.assign(window.I18N.ko, { rm_title: "복약 알림", rm_intro: "약 먹을 시간이나 관리 안내를 확인할 시간을 정해 두세요.", rm_type: "무엇을 알릴까요", rm_time: "시각", rm_repeat: "반복",
  rm_MEDICATION: "약 먹을 시간", rm_GUIDE_CHECK: "관리 안내 확인", rm_repeat_daily: "매일", rm_repeat_none: "한 번만", rm_add: "알림 추가", rm_list: "내 알림",
  rm_none: "아직 알림이 없어요.", rm_on: "켜기", rm_delete: "삭제", rm_alert_MEDICATION: "💊 약 먹을 시간이에요. 처방전에 적힌 대로 드세요.",
  rm_alert_GUIDE_CHECK: "📋 시술 후 관리 안내를 확인할 시간이에요.", rm_demo_note: "※ 데모 버전에서는 GlowPass 화면이 열려 있을 때만 알려요." });
Object.assign(window.I18N.ja, { rm_title: "服薬リマインダー", rm_intro: "お薬の時間やケア案内を確認する時間を設定しましょう。", rm_type: "通知の種類", rm_time: "時刻", rm_repeat: "繰り返し",
  rm_MEDICATION: "お薬の時間", rm_GUIDE_CHECK: "ケア案内の確認", rm_repeat_daily: "毎日", rm_repeat_none: "1回のみ", rm_add: "追加", rm_list: "マイ通知",
  rm_none: "まだ通知はありません。", rm_on: "オン", rm_delete: "削除", rm_alert_MEDICATION: "💊 お薬の時間です。処方どおりに服用してください。",
  rm_alert_GUIDE_CHECK: "📋 施術後のケア案内を確認する時間です。", rm_demo_note: "※ デモ版では GlowPass の画面を開いているときだけ通知します。" });
Object.assign(window.I18N.zh, { rm_title: "用药提醒", rm_intro: "设置吃药时间或查看护理说明的时间。", rm_type: "提醒内容", rm_time: "时间", rm_repeat: "重复",
  rm_MEDICATION: "吃药时间", rm_GUIDE_CHECK: "查看护理说明", rm_repeat_daily: "每天", rm_repeat_none: "仅一次", rm_add: "添加提醒", rm_list: "我的提醒",
  rm_none: "还没有提醒。", rm_on: "开启", rm_delete: "删除", rm_alert_MEDICATION: "💊 该吃药了。请按处方服用。",
  rm_alert_GUIDE_CHECK: "📋 该查看术后护理说明了。", rm_demo_note: "※ 演示版仅在 GlowPass 页面打开时提醒。" });
Object.assign(window.I18N.en, { rm_title: "Medication reminders", rm_intro: "Set times to take your medicine or check your care guide.", rm_type: "Remind me to", rm_time: "Time", rm_repeat: "Repeat",
  rm_MEDICATION: "Take medicine", rm_GUIDE_CHECK: "Check care guide", rm_repeat_daily: "Every day", rm_repeat_none: "Once", rm_add: "Add reminder", rm_list: "My reminders",
  rm_none: "No reminders yet.", rm_on: "On", rm_delete: "Delete", rm_alert_MEDICATION: "💊 Time for your medicine. Take it as prescribed.",
  rm_alert_GUIDE_CHECK: "📋 Time to check your aftercare guide.", rm_demo_note: "※ In the demo, reminders only appear while GlowPass is open." });
Object.assign(window.I18N.ko, { hc_already: "이 병원에 이미 진행 중인 요청이 있어요. '내 연락 요청'에서 확인하세요." });
Object.assign(window.I18N.ja, { hc_already: "この病院にはすでに進行中のリクエストがあります。「連絡リクエスト一覧」でご確認ください。" });
Object.assign(window.I18N.zh, { hc_already: "您对这家医院已有正在处理的请求，请在“我的联系请求”中查看。" });
Object.assign(window.I18N.en, { hc_already: "You already have an open request for this clinic. See 'My contact requests'." });
// 병원 접수대 화면 (데모: 관리자 계정이 병원 역할을 대신한다)
Object.assign(window.I18N.ko, { hd_title: "병원 접수대", hd_desc: "환자가 보낸 연락 요청을 확인하고 상태를 바꿉니다. (데모: 관리자 계정이 병원 역할)",
  hd_open_only: "진행 중만", hd_all: "끝난 것까지", hd_none: "처리할 요청이 없어요.", hd_requester: "요청자", hd_contact: "연락처", hd_lang: "언어",
  hd_start: "확인 시작", hd_done: "연락 완료", hd_about_record: "시술 기록 문의", hd_about_alert: "⚠ 위험 신호에서 넘어온 요청 — 먼저 확인",
  hd_refresh: "새로 고침" });
Object.assign(window.I18N.ja, { hd_title: "病院受付", hd_desc: "患者からの連絡リクエストを確認し、状態を変更します。（デモ：管理者が病院役）",
  hd_open_only: "進行中のみ", hd_all: "完了分も表示", hd_none: "処理するリクエストはありません。", hd_requester: "依頼者", hd_contact: "連絡先", hd_lang: "言語",
  hd_start: "確認開始", hd_done: "連絡完了", hd_about_record: "施術記録の問い合わせ", hd_about_alert: "⚠ 危険サインからのリクエスト — 先に確認",
  hd_refresh: "更新" });
Object.assign(window.I18N.zh, { hd_title: "医院前台", hd_desc: "查看患者发送的联系请求并更新状态。（演示：管理员代替医院）",
  hd_open_only: "仅进行中", hd_all: "含已结束", hd_none: "没有待处理的请求。", hd_requester: "请求者", hd_contact: "联系方式", hd_lang: "语言",
  hd_start: "开始确认", hd_done: "已联系", hd_about_record: "治疗记录咨询", hd_about_alert: "⚠ 来自危险信号的请求 — 请优先处理",
  hd_refresh: "刷新" });
Object.assign(window.I18N.en, { hd_title: "Clinic front desk", hd_desc: "Review contact requests from patients and update their status. (Demo: an admin account plays the clinic.)",
  hd_open_only: "Open only", hd_all: "Include closed", hd_none: "No requests to handle.", hd_requester: "Requester", hd_contact: "Contact", hd_lang: "Language",
  hd_start: "Start checking", hd_done: "Contacted", hd_about_record: "About a treatment record", hd_about_alert: "⚠ Came from a safety alert — check first",
  hd_refresh: "Refresh" });
// [배포 전 v2 F1] 가입 동의 (10/26 멘토링: 동의해야만 가입 · 없으면 앱 심사 반려) — 데모 서비스 · 법무 검토 전 초안
Object.assign(window.I18N.ko, {
  agree_privacy: "[필수] 개인정보 수집 · 이용 동의", agree_terms: "[필수] 이용약관 동의", agree_view: "내용 보기",
  privacy_full: "※ 데모 서비스 · 법무 검토 전 초안입니다.\n\n1. 수집 항목: 이메일, 비밀번호(암호화 저장), 이름, 성별, 생년월일, 휴대폰 번호, 연락용 메신저와 아이디, 국적, 화면 언어, 진료기록(병원·시술·처방), 처방전·약봉투 사진, 챗봇 질문\n2. 이용 목적: 복약 · 생활 관리 가이드 제공, 챗봇 답변, 사용자가 고른 병원에 연락 요청 전달\n3. 보유 기간: 회원 탈퇴 때까지 (탈퇴하면 바로 삭제). 챗봇 대화는 30일 뒤 자동 삭제\n4. 민감정보(건강정보) 처리: 진료기록 · 처방 · 사진은 건강에 관한 민감정보입니다. 위 목적에만 쓰며, 이 동의로 민감정보 처리에도 따로 동의합니다.\n5. 국외 이전: 이전받는 자 OpenAI(미국) · 항목: 진료기록 · 사진 · 챗봇 질문(질문 속 연락처 · 이메일 · 등록번호는 가린 뒤 보냄. 사진에 적힌 글자는 그대로 갈 수 있음) · 목적: AI 가이드 · 사진 인식 · 챗봇 답변 · 시기와 방법: 기능을 쓸 때마다 암호화된 통신으로 · 보유 기간: OpenAI 정책에 따름\n6. 동의를 거부할 권리: 동의하지 않을 수 있습니다. 다만 동의하지 않으면 가입과 서비스 이용이 어렵습니다.\n\n데모에는 실제 환자 정보를 넣지 마세요.",
  terms_full: "※ 데모 서비스 · 법무 검토 전 초안입니다.\n\n1. GlowPass 는 피부과 시술 뒤 관리를 돕는 정보 서비스이며, 진단 · 처방 · 특정 약 추천을 하지 않습니다.\n2. AI 안내는 참고용입니다. 증상이 심하거나 응급이면 바로 병원 또는 119 에 연락하세요.\n3. 병원은 사용자가 목록에서 직접 고릅니다. GlowPass 는 병원을 추천하거나 연결 수수료를 받지 않습니다.\n4. 다른 사람의 정보를 넣거나 서비스를 방해하면 이용이 제한될 수 있습니다.\n5. 언제든지 '회원 탈퇴'로 계정과 기록을 지울 수 있습니다.",
  agree_needed: "필수 동의 두 가지에 체크해 주세요.",
});
Object.assign(window.I18N.ja, {
  agree_privacy: "[必須] 個人情報の収集・利用への同意", agree_terms: "[必須] 利用規約への同意", agree_view: "内容を見る",
  privacy_full: "※ デモサービス・法務確認前の草案です。\n\n1. 収集項目：メール、パスワード（暗号化して保存）、氏名、性別、生年月日、携帯電話番号、連絡用メッセンジャーとID、国籍、表示言語、診療記録（病院・施術・処方）、処方箋・薬袋の写真、チャットボットへの質問\n2. 利用目的：服薬・生活ケアガイドの提供、チャットボットの回答、ご自身で選んだ病院への連絡リクエストの送信\n3. 保有期間：退会まで（退会するとすぐに削除）。チャットボットの会話は30日後に自動削除\n4. 要配慮個人情報（健康情報）の取扱い：診療記録・処方・写真は健康に関する情報です。上記の目的にのみ使い、この同意により健康情報の取扱いにも同意します。\n5. 国外移転：移転先 OpenAI（米国）・項目：診療記録・写真・チャットボットの質問（質問内の連絡先・メール・登録番号は伏せて送信。写真に写った文字はそのまま送られる場合あり）・目的：AIガイド・写真読み取り・チャットボットの回答・時期と方法：機能を使うたびに暗号化通信で・保有期間：OpenAIのポリシーによる\n6. 同意を拒否する権利：同意しないこともできます。ただし同意しない場合、登録とサービスの利用ができません。\n\nデモでは実際の患者情報を入力しないでください。",
  terms_full: "※ デモサービス・法務確認前の草案です。\n\n1. GlowPassは皮膚科施術後のケアを支援する情報サービスで、診断・処方・特定の薬の推奨は行いません。\n2. AIの案内は参考用です。症状が重い場合や緊急時はすぐに病院または119に連絡してください。\n3. 病院はご自身で一覧から選びます。GlowPassは病院の推薦や紹介手数料の受け取りを行いません。\n4. 他人の情報を入力したり、サービスを妨害したりすると利用を制限することがあります。\n5. いつでも「退会」でアカウントと記録を削除できます。",
  agree_needed: "必須の同意2つにチェックしてください。",
});
Object.assign(window.I18N.zh, {
  agree_privacy: "[必选] 同意收集和使用个人信息", agree_terms: "[必选] 同意使用条款", agree_view: "查看内容",
  privacy_full: "※ 演示服务 · 法务审核前的草案。\n\n1. 收集项目：邮箱、密码（加密保存）、姓名、性别、出生日期、手机号码、联系用通讯软件及账号、国籍、界面语言、就诊记录（医院·治疗·处方）、处方单·药袋照片、向聊天机器人提出的问题\n2. 使用目的：提供用药·生活护理指南、聊天机器人回答、向您自行选择的医院发送联系请求\n3. 保存期限：至注销账号为止（注销后立即删除）。聊天记录30天后自动删除\n4. 敏感信息（健康信息）处理：就诊记录·处方·照片属于健康相关的敏感信息，仅用于上述目的。本同意也包括对敏感信息处理的单独同意。\n5. 跨境传输：接收方 OpenAI（美国）· 项目：就诊记录·照片·聊天问题（问题中的联系方式·邮箱·证件号会先隐藏；照片上的文字可能原样发送）· 目的：AI指南·照片识别·聊天机器人回答 · 时间与方式：每次使用功能时通过加密通信传输 · 保存期限：依照 OpenAI 政策\n6. 拒绝同意的权利：您可以不同意，但不同意将无法注册和使用服务。\n\n演示时请勿填写真实患者信息。",
  terms_full: "※ 演示服务 · 法务审核前的草案。\n\n1. GlowPass 是帮助皮肤科治疗后护理的信息服务，不提供诊断、处方或推荐特定药物。\n2. AI 指南仅供参考。症状严重或紧急时，请立即联系医院或拨打 119。\n3. 医院由您自行从列表中选择。GlowPass 不推荐医院，也不收取介绍费。\n4. 填写他人信息或妨碍服务的，可能会被限制使用。\n5. 您可随时通过“注销账号”删除账号和记录。",
  agree_needed: "请勾选两项必选同意。",
});
Object.assign(window.I18N.en, {
  agree_privacy: "[Required] I agree to the collection and use of personal information", agree_terms: "[Required] I agree to the Terms of Use", agree_view: "View details",
  privacy_full: "※ Demo service · draft before legal review.\n\n1. What we collect: email, password (stored encrypted), name, gender, date of birth, mobile number, messenger and ID for contact, nationality, display language, medical records (clinic, treatment, prescription), photos of prescriptions or medicine bags, questions to the chatbot\n2. Why: to give medication and aftercare guides, answer chatbot questions, and send contact requests to a clinic you choose\n3. How long: until you delete your account (deleted right away). Chatbot conversations are deleted automatically after 30 days\n4. Sensitive (health) information: medical records, prescriptions and photos are sensitive health information. We use them only for the purposes above, and this consent also covers processing of sensitive information.\n5. Transfer abroad: recipient OpenAI (United States) · items: medical records, photos, chatbot questions (phone numbers, emails and ID numbers in questions are hidden first; text printed on photos may be sent as is) · purpose: AI guides, photo reading, chatbot answers · when and how: each time you use these features, over encrypted connections · retention: per OpenAI's policy\n6. Your right to refuse: you may refuse, but without consent you cannot sign up or use the service.\n\nDo not enter real patient information in demos.",
  terms_full: "※ Demo service · draft before legal review.\n\n1. GlowPass is an information service for aftercare following dermatology treatments. It does not diagnose, prescribe or recommend specific medicines.\n2. AI guidance is for reference only. If symptoms are severe or it is an emergency, contact a clinic or call 119 right away.\n3. You choose clinics yourself from the list. GlowPass does not recommend clinics or take referral fees.\n4. Entering someone else's information or disrupting the service may lead to restricted use.\n5. You can delete your account and records at any time with 'Delete account'.",
  agree_needed: "Please check both required agreements.",
});
// [배포 전 v2 F2] 연락처는 가린 값만 화면에 — 병원은 연락 요청으로 원래 연락처를 받는다
Object.assign(window.I18N.ko, { card_contact_note: "등록하신 연락처로 병원이 연락합니다" });
Object.assign(window.I18N.ja, { card_contact_note: "ご登録の連絡先に病院から連絡します" });
Object.assign(window.I18N.zh, { card_contact_note: "医院将通过您登记的联系方式与您联系" });
Object.assign(window.I18N.en, { card_contact_note: "The clinic will contact you using your registered contact details" });
