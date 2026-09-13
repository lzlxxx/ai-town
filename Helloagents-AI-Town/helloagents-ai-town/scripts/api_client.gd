# API客户端 - 与FastAPI后端通信
extends Node

# 信号定义
signal chat_response_received(npc_name: String, message: String, emotion: Dictionary)
signal chat_error(error_message: String)
signal npc_status_received(dialogues: Dictionary)
signal npc_list_received(npcs: Array)
signal tasks_received(tasks: Array)
signal task_accept_result(task: Dictionary)
signal task_error(error_message: String)

# HTTP请求节点
var http_chat: HTTPRequest
var http_status: HTTPRequest
var http_npcs: HTTPRequest
var http_tasks: HTTPRequest
var http_task_accept: HTTPRequest

func _ready():
	# 创建HTTP请求节点
	http_chat = HTTPRequest.new()
	http_status = HTTPRequest.new()
	http_npcs = HTTPRequest.new()
	http_tasks = HTTPRequest.new()
	http_task_accept = HTTPRequest.new()
	
	add_child(http_chat)
	add_child(http_status)
	add_child(http_npcs)
	add_child(http_tasks)
	add_child(http_task_accept)
	
	# 连接信号
	http_chat.request_completed.connect(_on_chat_request_completed)
	http_status.request_completed.connect(_on_status_request_completed)
	http_npcs.request_completed.connect(_on_npcs_request_completed)
	http_tasks.request_completed.connect(_on_tasks_request_completed)
	http_task_accept.request_completed.connect(_on_task_accept_request_completed)
	
	print("[INFO] API客户端初始化完成")

# ==================== 对话API ====================
func send_chat(npc_name: String, message: String) -> void:
	"""发送对话请求"""
	var data = {
		"npc_name": npc_name,
		"message": message
	}
	
	var json_string = JSON.stringify(data)
	var headers = ["Content-Type: application/json"]
	
	print("[API] POST /chat -> ", data)
	
	var error = http_chat.request(
		Config.API_CHAT,
		headers,
		HTTPClient.METHOD_POST,
		json_string
	)
	
	if error != OK:
		print("[ERROR] 发送对话请求失败: ", error)
		chat_error.emit("网络请求失败")

func _on_chat_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	"""处理对话响应"""
	if response_code != 200:
		print("[ERROR] 对话请求失败: HTTP ", response_code)
		chat_error.emit("服务器错误: " + str(response_code))
		return
	
	var json = JSON.new()
	var parse_result = json.parse(body.get_string_from_utf8())
	
	if parse_result != OK:
		print("[ERROR] 解析响应失败")
		chat_error.emit("响应解析失败")
		return
	
	var response = json.data
	
	if response.has("success") and response["success"]:
		var npc_name = response["npc_name"]
		var msg = response["message"]
		var emotion = response.get("emotion", {})
		# 将后端返回的好感度合并到情绪摘要，保持现有信号兼容。
		if response.has("affinity"):
			emotion = emotion.duplicate()
			emotion["affinity"] = response["affinity"]
		print("[INFO] 收到NPC回复: ", npc_name, " -> ", msg)
		chat_response_received.emit(npc_name, msg, emotion)
		get_tasks()
	else:
		chat_error.emit("对话失败")

# ==================== 任务API ====================
func get_tasks() -> void:
	"""获取任务列表"""
	if http_tasks.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		print("[WARN] 任务列表请求正在处理中,跳过本次请求")
		return

	print("[API] GET /tasks")

	var error = http_tasks.request(Config.API_TASKS)
	if error != OK:
		print("[ERROR] 获取任务列表失败: ", error)
		task_error.emit("任务列表请求失败")

func accept_task(task_id: String) -> void:
	"""接受任务"""
	if http_task_accept.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		print("[WARN] 任务接受请求正在处理中,跳过本次请求")
		return

	var headers = ["Content-Type: application/json"]
	var url = Config.API_TASKS + "/" + task_id + "/accept"
	print("[API] POST ", url)

	var error = http_task_accept.request(
		url,
		headers,
		HTTPClient.METHOD_POST,
		""
	)

	if error != OK:
		print("[ERROR] 接受任务失败: ", error)
		task_error.emit("接受任务请求失败")

func _on_tasks_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	"""处理任务列表响应"""
	if response_code != 200:
		print("[ERROR] 任务列表请求失败: HTTP ", response_code)
		task_error.emit("任务列表服务器错误: " + str(response_code))
		return

	var response = _parse_json_body(body)
	if response == null:
		task_error.emit("任务列表解析失败")
		return

	if response.has("tasks"):
		var tasks = response["tasks"]
		print("[INFO] 收到任务列表: ", tasks.size(), "个任务")
		tasks_received.emit(tasks)

func _on_task_accept_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	"""处理任务接受响应"""
	var response = _parse_json_body(body)

	if response_code != 200:
		var detail = "接受任务失败: HTTP " + str(response_code)
		if response != null and response.has("detail"):
			detail = str(response["detail"])
		print("[ERROR] ", detail)
		task_error.emit(detail)
		return

	if response == null:
		task_error.emit("任务接受响应解析失败")
		return

	if response.has("success") and response["success"]:
		var task = response.get("task", {})
		print("[INFO] 任务接受成功: ", task.get("title", ""))
		task_accept_result.emit(task)
		get_tasks()
	else:
		task_error.emit(str(response.get("reason", "任务接受失败")))

func _parse_json_body(body: PackedByteArray):
	"""解析JSON响应体"""
	var json = JSON.new()
	var parse_result = json.parse(body.get_string_from_utf8())

	if parse_result != OK:
		print("[ERROR] 解析JSON响应失败")
		return null

	return json.data

# ==================== NPC状态API ====================
func get_npc_status() -> void:
	"""获取NPC状态"""
	# 检查是否正在处理请求
	if http_status.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		print("[WARN] NPC状态请求正在处理中,跳过本次请求")
		return

	print("[API] GET /npcs/status")

	var error = http_status.request(Config.API_NPC_STATUS)

	if error != OK:
		print("[ERROR] 获取NPC状态失败: ", error)

func _on_status_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	"""处理NPC状态响应"""
	if response_code != 200:
		print("[ERROR] NPC状态请求失败: HTTP ", response_code)
		return
	
	var json = JSON.new()
	var parse_result = json.parse(body.get_string_from_utf8())
	
	if parse_result != OK:
		print("[ERROR] 解析NPC状态失败")
		return
	
	var response = json.data
	
	if response.has("dialogues"):
		var dialogues = response["dialogues"]
		print("[INFO] 收到NPC状态更新: ", dialogues.size(), "个NPC")
		npc_status_received.emit(dialogues)

# ==================== NPC列表API ====================
func get_npc_list() -> void:
	"""获取NPC列表"""
	print("[API] GET /npcs")
	
	var error = http_npcs.request(Config.API_NPCS)
	
	if error != OK:
		print("[ERROR] 获取NPC列表失败: ", error)

func _on_npcs_request_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	"""处理NPC列表响应"""
	if response_code != 200:
		print("[ERROR] NPC列表请求失败: HTTP ", response_code)
		return
	
	var json = JSON.new()
	var parse_result = json.parse(body.get_string_from_utf8())
	
	if parse_result != OK:
		print("[ERROR] 解析NPC列表失败")
		return
	
	var response = json.data
	
	if response.has("npcs"):
		var npcs = response["npcs"]
		print("[INFO] 收到NPC列表: ", npcs.size(), "个NPC")
		npc_list_received.emit(npcs)
