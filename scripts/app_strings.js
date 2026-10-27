// [앱 v1 3] 앱에만 있는 문구 (웹에 없는 것: 수정·삭제·입력 검사·휴대폰 알림 권한 등) — 4개 언어를 모두 채운다
//   쓰는 법: node scripts/app_strings.js → res/values*/strings_app.xml
const fs = require("fs");
const path = require("path");
const S = {
  features: ["기능 바로가기", "All features", "機能一覧", "功能入口"],
  profile_title: ["내 정보", "My info", "マイ情報", "我的信息"],
  profile_save: ["저장", "Save", "保存", "保存"],
  profile_saved: ["저장했어요.", "Saved.", "保存しました。", "已保存。"],
  profile_masked_note: ["연락처는 가려서 보여 줘요. 바꿀 때만 새로 입력하세요.", "Contact details are shown masked. Enter new ones only to change them.", "連絡先は一部を隠して表示します。変更するときだけ新しく入力してください。", "联系方式会部分隐藏显示。仅在需要修改时重新输入。"],
  profile_lang: ["화면 언어", "Display language", "表示言語", "界面语言"],
  edit: ["수정", "Edit", "編集", "编辑"],
  delete: ["삭제", "Delete", "削除", "删除"],
  cancel: ["취소", "Cancel", "キャンセル", "取消"],
  ok: ["확인", "OK", "OK", "确定"],
  retry: ["다시 시도", "Try again", "再試行", "重试"],
  loading: ["불러오는 중…", "Loading…", "読み込み中…", "加载中…"],
  record_edit_title: ["진료기록 수정", "Edit medical record", "診療記録の編集", "编辑就诊记录"],
  record_update: ["수정 저장", "Save changes", "変更を保存", "保存修改"],
  record_delete_confirm: ["이 진료기록을 지울까요? 지운 기록은 되돌릴 수 없어요.", "Delete this medical record? This cannot be undone.", "この診療記録を削除しますか？元に戻せません。", "要删除这条就诊记录吗？删除后无法恢复。"],
  record_deleted: ["진료기록을 지웠어요.", "Medical record deleted.", "診療記録を削除しました。", "已删除就诊记录。"],
  record_detail: ["기록 보기", "View record", "記録を見る", "查看记录"],
  guides_none: ["아직 만든 가이드가 없어요.", "No guides yet.", "まだガイドがありません。", "还没有指南。"],
  guide_context_title: ["가이드에 쓰이는 최근 기록 요약", "Summary of recent records used for guides", "ガイドに使われる最近の記録の要約", "用于指南的近期记录摘要"],
  ocr_camera: ["📷 사진 찍기", "📷 Take a photo", "📷 写真を撮る", "📷 拍照"],
  ocr_gallery: ["🖼 갤러리에서 고르기", "🖼 Choose from gallery", "🖼 ギャラリーから選ぶ", "🖼 从相册选择"],
  val_required: ["필수 칸을 채워 주세요.", "Please fill in the required fields.", "必須項目を入力してください。", "请填写必填项。"],
  val_email: ["이메일 형식을 확인해 주세요.", "Please check the email format.", "メールアドレスの形式を確認してください。", "请检查邮箱格式。"],
  val_phone: ["휴대폰 번호 형식을 확인해 주세요. (예: 01012345678 또는 +86 138 1234 5678)", "Please check the phone number. (e.g. 01012345678 or +86 138 1234 5678)", "電話番号の形式を確認してください。（例: 01012345678 または +86 138 1234 5678）", "请检查手机号码格式。（例：01012345678 或 +86 138 1234 5678）"],
  val_messenger: ["메신저 아이디는 2~50자의 글자·숫자·_ . - + @ 만 쓸 수 있어요.", "Messenger ID: 2–50 letters, numbers or _ . - + @ only.", "メッセンジャーIDは2〜50文字の文字・数字・_ . - + @ のみ使えます。", "通讯软件账号为2~50个字符，只能使用字母、数字及 _ . - + @。"],
  val_birth: ["만 14세 이상만 가입할 수 있어요.", "You must be 14 or older to sign up.", "14歳以上の方のみ登録できます。", "仅限14岁以上用户注册。"],
  val_gender: ["성별을 선택해 주세요.", "Please select your gender.", "性別を選択してください。", "请选择性别。"],
  val_date: ["날짜는 YYYY-MM-DD 형식으로 입력해 주세요.", "Please enter the date as YYYY-MM-DD.", "日付は YYYY-MM-DD の形式で入力してください。", "请按 YYYY-MM-DD 格式输入日期。"],
  val_future: ["진료일은 오늘 이후일 수 없어요.", "The visit date cannot be in the future.", "診療日に未来の日付は指定できません。", "就诊日期不能晚于今天。"],
  val_number: ["숫자를 확인해 주세요. (하루 1~10회, 1~365일분)", "Please check the numbers. (1–10 times a day, 1–365 days)", "数字を確認してください。（1日1〜10回、1〜365日分）", "请检查数字。（每天1~10次，1~365天）"],
  val_name: ["이름은 2~50자로 입력해 주세요.", "Please enter a name of 2–50 characters.", "名前は2〜50文字で入力してください。", "姓名请输入2~50个字符。"],
  session_expired: ["로그인이 끝났어요. 다시 로그인해 주세요.", "Your session has ended. Please log in again.", "ログインの有効期限が切れました。もう一度ログインしてください。", "登录已过期，请重新登录。"],
  network_error: ["서버에 연결하지 못했어요. 인터넷 연결을 확인해 주세요.", "Could not reach the server. Please check your internet connection.", "サーバーに接続できませんでした。インターネット接続を確認してください。", "无法连接服务器，请检查网络连接。"],
  rm_app_note: ["앱을 닫아도 정한 시각에 휴대폰 알림이 와요.", "You will get a phone notification at the set time even if the app is closed.", "アプリを閉じていても、設定した時刻にスマホへ通知が届きます。", "即使关闭应用，也会在设定时间收到手机通知。"],
  rm_perm_denied: ["알림 권한이 꺼져 있어 휴대폰 알림을 보낼 수 없어요. 설정에서 켜 주세요.", "Notifications are turned off, so we cannot alert you. Please turn them on in Settings.", "通知がオフのため、スマホに通知できません。設定でオンにしてください。", "通知权限已关闭，无法发送手机通知。请在设置中开启。"],
  rm_exact_off: ["정확한 시각 알람이 꺼져 있어 알림이 몇 분 늦게 올 수 있어요.", "Exact alarms are off, so notifications may arrive a few minutes late.", "正確なアラームがオフのため、通知が数分遅れることがあります。", "精确闹钟未开启，通知可能会晚几分钟。"],
  rm_exact_open: ["정확한 알람 허용하기", "Allow exact alarms", "正確なアラームを許可", "允许精确闹钟"],
  rm_channel: ["복약 알림", "Medication reminders", "服薬リマインダー", "用药提醒"],
  open_settings: ["설정 열기", "Open settings", "設定を開く", "打开设置"],
  chat_usage: ["오늘 질문 {used} / {limit}", "Questions today {used} / {limit}", "今日の質問 {used} / {limit}", "今日提问 {used} / {limit}"],
  chat_alerts: ["내 위험 신호 기록", "My safety alerts", "危険サインの記録", "我的危险信号记录"],
  chat_alerts_none: ["위험 신호 기록이 없어요.", "No safety alerts.", "危険サインの記録はありません。", "没有危险信号记录。"],
  chat_stop: ["멈추기", "Stop", "停止", "停止"],
  chat_lang: ["챗봇 언어", "Chatbot language", "チャットボットの言語", "聊天机器人语言"],
  tts_unsupported_app: ["이 휴대폰은 음성 읽기를 지원하지 않아요.", "This phone does not support text-to-speech.", "このスマホは音声読み上げに対応していません。", "此手机不支持语音朗读。"],
  card_shared: ["카드 이미지를 만들었어요. 저장하거나 보낼 앱을 고르세요.", "Card image ready. Choose where to save or send it.", "カード画像を作りました。保存先・送信先を選んでください。", "卡片图片已生成，请选择保存或发送的应用。"],
  guide_assets: ["변환 파일 {n}개 (관리자)", "{n} converted files (admin)", "変換ファイル {n}件（管理者）", "转换文件 {n} 个（管理员）"],
  hosp_detail: ["병원 정보", "Clinic info", "病院情報", "医院信息"],
  contact_detail: ["요청 자세히", "Request details", "依頼の詳細", "请求详情"],
  app_version: ["앱 버전 {v} · 서버 {s}", "App {v} · server {s}", "アプリ {v} ・ サーバー {s}", "应用 {v} · 服务器 {s}"],
};
const DIRS = ["values", "values-en", "values-ja", "values-zh"];
const esc = (s) => String(s)
  .replace(/\\/g, "\\\\").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, "\\n").replace(/^([@?])/, "\\$1");
DIRS.forEach((dir, i) => {
  const out = ['<?xml version="1.0" encoding="utf-8"?>',
    "<!-- 자동 생성: scripts/app_strings.js — 앱에만 있는 문구 (4개 언어) -->", "<resources>"];
  if (i === 0) out.push('    <string name="app_name" translatable="false">GlowPass</string>');
  for (const [k, v] of Object.entries(S)) out.push(`    <string name="${k}" formatted="false">${esc(v[i])}</string>`);
  out.push("</resources>", "");
  fs.writeFileSync(path.join(__dirname, "..", "app", "src", "main", "res", dir, "strings_app.xml"), out.join("\n"));
  console.log(dir, Object.keys(S).length);
});
