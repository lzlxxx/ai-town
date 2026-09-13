# 对话UI脚本
extends CanvasLayer

# 节点引用
@onready var panel: Panel = $Panel
@onready var npc_name_label: Label = $Panel/NPCName
@onready var npc_title_label: Label = $Panel/NPCTitle
@onready var emotion_label: Label = $Panel/EmotionLabel
@onready var dialogue_text: RichTextLabel = $Panel/DialogueText
@onready var player_input: LineEdit = $Panel/PlayerInput
@onready var send_button: Button = $Panel/SendButton
@onready var close_button: Button = $Panel/CloseButton

# 当前对话的NPC
var current_npc_name: String = ""

# 本局游戏内按NPC保存的可见聊天记录
var dialogue_histories: Dictionary = {}

# 本局游戏内按NPC保存的当前情绪摘要
var npc_emotions: Dictionary = {}

# APIClient当前只使用一个HTTP聊天请求节点,所以前端一次只发送一条消息
var pending_npc_name: String = ""
var last_submit_msec: int = 0

# API客户端引用
var api_client: Node = null

func _ready():
	# 添加到对话系统组
	add_to_group("dialogue_system")

	# 初始隐藏
	visible = false

	# 连接按钮信号
	send_button.pressed.connect(_on_send_button_pressed)
	close_button.pressed.connect(_on_close_button_pressed)
	player_input.text_submitted.connect(_on_text_submitted)

	# 获取API客户端
	api_client = get_node_or_null("/root/APIClient")
	if api_client:
		api_client.chat_response_received.connect(_on_chat_response_received)
		api_client.chat_error.connect(_on_chat_error)

	print("[INFO] 对话UI初始化完成")

# ⭐ 处理对话框快捷键
func _input(event: InputEvent):
	# 如果对话框不可见,不处理
	if not visible:
		return

	if event is InputEventKey and event.pressed and not event.echo:
		# ESC键 - 关闭对话框 
		if event.keycode == KEY_ESCAPE:
			hide_dialogue()
			get_viewport().set_input_as_handled()
			print("[DEBUG] ESC键关闭对话框")
			return

		# 回车键 - 对话框可见时统一发送消息
		if event.keycode == KEY_ENTER or event.keycode == KEY_KP_ENTER:
			_submit_message()
			get_viewport().set_input_as_handled()
			print("[DEBUG] 回车键发送消息")
			return

		# 屏蔽移动键和交互键,防止触发游戏操作 ⭐ WASD键
		if event.keycode in [KEY_E, KEY_SPACE, KEY_W, KEY_A, KEY_S, KEY_D]:
			get_viewport().set_input_as_handled()
			# 只在第一次屏蔽时打印,避免刷屏
			match event.keycode:
				KEY_E:
					print("[DEBUG] 对话框中屏蔽了E键输入")
				KEY_SPACE:
					print("[DEBUG] 对话框中屏蔽了空格键输入")
				KEY_W:
					print("[DEBUG] 对话框中屏蔽了W键输入")
				KEY_A:
					print("[DEBUG] 对话框中屏蔽了A键输入")
				KEY_S:
					print("[DEBUG] 对话框中屏蔽了S键输入")
				KEY_D:
					print("[DEBUG] 对话框中屏蔽了D键输入")

func start_dialogue(npc_name: String):
	"""开始与NPC对话"""
	current_npc_name = npc_name

	# 通知NPC进入交互状态 (停止移动) 
	var npc = get_npc_by_name(npc_name)
	if npc and npc.has_method("set_interacting"):
		npc.set_interacting(true)

		# 设置NPC信息
		npc_name_label.text = npc_name
		npc_title_label.text = Config.NPC_TITLES.get(npc_name, "")
		_render_emotion_label()

	# 显示本局游戏内已保存的对话内容
	_render_dialogue_history()

	# 清空输入框
	player_input.text = ""

	# 显示对话框
	show_dialogue()

	# 聚焦输入框
	player_input.grab_focus()

	print("[INFO] 开始对话: ", npc_name)

func show_dialogue():
	"""显示对话框"""
	visible = true

	# 通知玩家进入交互状态 (禁用移动)
	var player = get_tree().get_first_node_in_group("player")
	if player and player.has_method("set_interacting"):
		player.set_interacting(true)

func hide_dialogue():
	"""隐藏对话框"""
	visible = false

	# 通知NPC退出交互状态 (恢复移动) 
	if current_npc_name != "":
		var npc = get_npc_by_name(current_npc_name)
		if npc and npc.has_method("set_interacting"):
			npc.set_interacting(false)

	current_npc_name = ""

	# 通知玩家退出交互状态 (启用移动)
	var player = get_tree().get_first_node_in_group("player")
	if player and player.has_method("set_interacting"):
		player.set_interacting(false)

func _on_send_button_pressed():
	"""发送按钮点击"""
	_submit_message()

func _on_text_submitted(_text: String):
	"""输入框回车"""
	_submit_message()

func _submit_message():
	"""统一处理发送按钮和Enter键"""
	var now = Time.get_ticks_msec()
	if now - last_submit_msec < 100:
		return

	if send_message():
		last_submit_msec = now

func send_message() -> bool:
	"""发送消息"""
	var message = player_input.text.strip_edges()
	
	if message.is_empty():
		return false
	
	if current_npc_name.is_empty():
		print("[ERROR] 没有选择NPC")
		return false

	if not pending_npc_name.is_empty():
		print("[WARN] 上一条消息还在等待回复")
		return false

	var npc_name = current_npc_name

	# 保存并显示玩家消息
	_add_dialogue_entry(npc_name, "玩家", message, "cyan")
	
	# 清空输入框
	player_input.text = ""
	
	# 显示等待提示
	pending_npc_name = npc_name
	_render_dialogue_history()
	
	# 发送API请求
	if api_client:
		api_client.send_chat(npc_name, message)
	else:
		print("[ERROR] API客户端未找到")
		_on_chat_error("API客户端未找到")
		return false

	return true

func _on_chat_response_received(npc_name: String, message: String, emotion: Dictionary):
	"""收到NPC回复"""
	if not emotion.is_empty():
		npc_emotions[npc_name] = emotion

	_add_dialogue_entry(npc_name, npc_name, message, "yellow")
	
	if pending_npc_name == npc_name:
		pending_npc_name = ""

	if npc_name == current_npc_name:
		_render_emotion_label()
		_render_dialogue_history()
		player_input.grab_focus()

func _on_chat_error(error_message: String):
	"""对话错误"""
	var npc_name = pending_npc_name
	if npc_name.is_empty():
		npc_name = current_npc_name

	if npc_name.is_empty():
		print("[ERROR] 对话错误: ", error_message)
		return

	_add_dialogue_entry(npc_name, "系统", "错误: " + error_message, "red")

	if pending_npc_name == npc_name:
		pending_npc_name = ""

	if npc_name == current_npc_name:
		_render_dialogue_history()
		player_input.grab_focus()

func _on_close_button_pressed():
	"""关闭按钮点击"""
	hide_dialogue()

# ⭐ 根据名字获取NPC节点
func get_npc_by_name(npc_name: String) -> Node:
	"""根据名字获取NPC节点"""
	var npcs = get_tree().get_nodes_in_group("npcs")
	for npc in npcs:
		if npc.npc_name == npc_name:
			return npc
	return null

func _ensure_dialogue_history(npc_name: String) -> Array:
	"""确保指定NPC有本局可见聊天记录"""
	if not dialogue_histories.has(npc_name):
		dialogue_histories[npc_name] = []
	return dialogue_histories[npc_name]

func _add_dialogue_entry(npc_name: String, speaker: String, message: String, color: String):
	"""写入指定NPC的本局可见聊天记录"""
	var history = _ensure_dialogue_history(npc_name)
	history.append({
		"speaker": speaker,
		"message": message,
		"color": color
	})

func _render_dialogue_history():
	"""渲染当前NPC的本局可见聊天记录"""
	dialogue_text.clear()

	if current_npc_name.is_empty():
		return

	var history = _ensure_dialogue_history(current_npc_name)
	if history.is_empty():
		dialogue_text.append_text("[color=gray]与 " + current_npc_name + " 的对话开始...[/color]\n")
	else:
		dialogue_text.append_text("[color=gray]继续与 " + current_npc_name + " 的对话...[/color]\n")

	for entry in history:
		var speaker = str(entry.get("speaker", ""))
		var message = _escape_bbcode(str(entry.get("message", "")))
		var color = str(entry.get("color", "white"))
		dialogue_text.append_text("[color=" + color + "]" + speaker + ":[/color] " + message + "\n")

	if pending_npc_name == current_npc_name:
		dialogue_text.append_text("[color=gray]等待回复...[/color]\n")

		send_button.disabled = not pending_npc_name.is_empty()
		dialogue_text.scroll_to_line(max(0, dialogue_text.get_line_count() - 1))

func _render_emotion_label():
	"""渲染当前NPC情绪摘要"""
	if current_npc_name.is_empty():
		emotion_label.text = ""
		return

	var emotion = npc_emotions.get(current_npc_name, {})
	var affinity = float(emotion.get("affinity", 50.0))
	if emotion.is_empty():
		emotion_label.text = "情绪：平静（强度 0/100）    好感度：" + str(roundf(affinity)) + "/100"
		emotion_label.add_theme_color_override("font_color", Color(0.68, 0.72, 0.78))
		return

	var label = str(emotion.get("label", "平静"))
	var intensity = float(emotion.get("intensity", 0.0))
	var level_label = str(emotion.get("level_label", "低"))
	var dominant = str(emotion.get("dominant", "neutral"))

	emotion_label.text = "情绪：" + label + "（强度 " + str(roundi(intensity)) + "/100）    好感度：" + str(roundf(affinity)) + "/100"
	emotion_label.add_theme_color_override("font_color", _emotion_color(dominant))

func _emotion_color(dominant: String) -> Color:
	match dominant:
		"joy":
			return Color(0.38, 0.82, 0.55)
		"sadness":
			return Color(0.46, 0.65, 1.0)
		"anger":
			return Color(1.0, 0.38, 0.32)
		"excitement":
			return Color(1.0, 0.72, 0.28)
		_:
			return Color(0.68, 0.72, 0.78)

func _escape_bbcode(value: String) -> String:
	"""避免玩家输入中的BBCode影响富文本显示"""
	return value.replace("[", "[lb]")
