#!/bin/bash

# 默认值设置
DEFAULT_PRODUCT_TYPE="none"
DEFAULT_ASCEND_EXPECTED=16
DEFAULT_CHECK_MEM_CPU="off"  # 新增：默认不检查内存/CPU

JQ_AVAILABLE=0

# 产品类型定义（可根据实际环境配置）
declare -A PRODUCT_TYPES=(
    ["none"]="不检测标签"
    ["full-910"]="Atlas 800 训练服务器（NPU满配）"
    ["half-910"]="Atlas 800 训练服务器（NPU半配）"
    ["a2-pod"]="Atlas 800T A2 训练服务器/Atlas 900 A2 PoD 集群基础单元"
    ["a3-superpod"]="Atlas 900 A3 SuperPoD 超节点/Atlas 9000 A3 SuperPoD 集群算力系统/Atlas 800T A3 超节点服务器"
    ["a3-box8"]="A200T A3 Box8 超节点服务器/Atlas 800I A3 超节点服务器"
    ["a2-infer"]="Atlas 800I A2 推理服务器"
    ["a2-box"]="A200I A2 Box 异构组件"
    ["a2-box16"]="Atlas 200T A2 Box16 异构子框"
    ["train-card"]="训练服务器（插Atlas 300T 训练卡）"
    ["infer-card"]="推理服务器（插Atlas 300I 推理卡）"
    ["infer-series"]="Atlas 推理系列产品"
    ["soc-core"]="Atlas 200I SoC A1 核心板"
)

# 处理帮助参数
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo "用法: ./envCheck.sh [期望NPU卡数量] [产品类型] [-r|--resources]"
    echo "      ./envCheck.sh [产品类型] [-r|--resources]            # 不传期望卡数时将自动识别资源类型并以第一个Ready节点卡数为准"
    echo "示例:"
    echo "  ./envCheck.sh                   # 使用默认配置（自动识别资源类型,并以第一个Ready节点的卡数为期望卡数,none不检测标签）"
    echo "  ./envCheck.sh  8                # 8卡,none不检测标签"
    echo "  ./envCheck.sh  8 -r             # 8卡,none不检测标签,同时检查内存和CPU资源"
    echo "  ./envCheck.sh  16               # 16卡,none不检测标签"
    echo "  ./envCheck.sh  8 full-910       # 使用满配服务器配置"
    echo "  ./envCheck.sh  4 half-910       # 使用半配服务器配置"
    echo "  ./envCheck.sh  8 full-910 -r    # 同时检查内存和CPU资源"
    echo ""
    echo "选项:"
    echo "  -r, --resources  启用内存和CPU资源检查"
    echo ""
    echo "可用产品类型列表："
    for type in "${!PRODUCT_TYPES[@]}"; do
        printf "  %-15s : %s\n" "$type" "${PRODUCT_TYPES[$type]}"
    done
    exit 0
fi

# 新增：处理资源检查选项
CHECK_MEM_CPU="$DEFAULT_CHECK_MEM_CPU"
new_args=()
for arg in "$@"; do
    if [[ "$arg" == "-r" || "$arg" == "--resources" ]]; then
        CHECK_MEM_CPU="on"
    else
        new_args+=("$arg")
    fi
done
set -- "${new_args[@]}"

# 处理位置参数
# - 支持两种方式：
#   1) ./envCheck.sh <期望卡数> <产品类型>
#   2) ./envCheck.sh <产品类型>              (不传期望卡数时自动探测：以第一个Ready节点为准)
ASCEND_EXPECTED=""
PRODUCT_TYPE="$DEFAULT_PRODUCT_TYPE"
ASCEND_RESOURCE_NAME=""      # 全局：实际检测使用的资源名（自动探测/或由产品形态推导）
ASCEND_EXPECTED_AUTO=0       # 全局：是否启用自动探测期望卡数

if [[ -n "$1" && "$1" =~ ^[0-9]+$ ]]; then
    ASCEND_EXPECTED="$1"
    PRODUCT_TYPE="${2:-$DEFAULT_PRODUCT_TYPE}"
elif [[ -n "$1" && -n "${PRODUCT_TYPES[$1]}" ]]; then
    # 第一个参数是产品类型（用户未传期望卡数）
    PRODUCT_TYPE="$1"
    ASCEND_EXPECTED_AUTO=1
else
    # 完全未提供期望卡数（也未提供产品类型）：启用自动探测
    ASCEND_EXPECTED_AUTO=1
    PRODUCT_TYPE="${1:-$DEFAULT_PRODUCT_TYPE}"
fi

# 若未启用自动探测,则要求期望卡数为数字
if [[ $ASCEND_EXPECTED_AUTO -eq 0 ]]; then
    if [[ -z "$ASCEND_EXPECTED" || ! "$ASCEND_EXPECTED" =~ ^[0-9]+$ ]]; then
        echo "错误：期望NPU卡数量必须是整数"
        exit 1
    fi
fi

# 验证产品类型是否有效
if [[ -z "${PRODUCT_TYPES[$PRODUCT_TYPE]}" ]]; then
    echo "错误：未知的产品类型 '$PRODUCT_TYPE'"
    echo "可用产品类型: ${!PRODUCT_TYPES[@]}"
    exit 1
fi

# 显示配置
echo "使用配置(如不符合默认配置,可使用bash envCheck.sh -h查看帮助信息,调整入参):"
if [[ $ASCEND_EXPECTED_AUTO -eq 1 ]]; then
    echo "  - 期望NPU卡数: 自动(以第一个Ready节点为准)"
else
    echo "  - 期望NPU卡数: $ASCEND_EXPECTED"
fi
echo "  - 产品类型: $PRODUCT_TYPE (${PRODUCT_TYPES[$PRODUCT_TYPE]})"
echo "  - 内存/CPU检查: $CHECK_MEM_CPU (可使用-r参数开启)"  # 新增配置显示

# 产品标签要求配置（可按需修改）
declare -A PRODUCT_LABEL_REQUIREMENTS=(
    # 公共标签（所有产品类型都需要）
    ["common"]="node-role.kubernetes.io/worker=worker workerselector=dls-worker-node"

    # 不检测标签
    ["none"]=""
    # Atlas 800 训练服务器（NPU满配）
    ["full-910"]="host-arch=huawei-arm|huawei-x86 accelerator=huawei-Ascend910 accelerator-type=module"
    # Atlas 800 训练服务器（NPU半配）
    ["half-910"]="host-arch=huawei-arm|huawei-x86 accelerator=huawei-Ascend910 accelerator-type=half"
    # Atlas 800T A2 训练服务器或Atlas 900 A2 PoD
    ["a2-pod"]="host-arch=huawei-arm accelerator=huawei-Ascend910 accelerator-type=module-.*b-8"
    # Atlas 900 A3 SuperPoD/Atlas 9000 A3 SuperPoD/Atlas 800T A3
    ["a3-superpod"]="host-arch=huawei-arm|huawei-x86 accelerator=huawei-Ascend910"
    # A200T A3 Box8/Atlas 800I A3
    ["a3-box8"]="host-arch=huawei-x86|huawei-arm accelerator=huawei-Ascend910 accelerator-type=module-a3-16"
    # Atlas 800I A2 推理服务器
    ["a2-infer"]="host-arch=huawei-arm accelerator=huawei-Ascend910 accelerator-type=module-.*b-8 server-usage=infer"
    # A200I A2 Box 异构组件
    ["a2-box"]="host-arch=huawei-x86 accelerator=huawei-Ascend910 accelerator-type=module-.*b-8 server-usage=infer"
    # Atlas 200T A2 Box16 异构子框
    ["a2-box16"]="host-arch=huawei-x86 accelerator=huawei-Ascend910 accelerator-type=module-.*b-16"
    # 训练服务器（插Atlas 300T 训练卡）
    ["train-card"]="host-arch=huawei-arm|huawei-x86 accelerator=huawei-Ascend910 accelerator-type=card"
    # 推理服务器（插Atlas 300I 推理卡）
    ["infer-card"]="host-arch=huawei-arm|huawei-x86 accelerator=huawei-Ascend310"
    # Atlas 推理系列产品
    ["infer-series"]="host-arch=huawei-arm|huawei-x86 accelerator=huawei-Ascend310P"
    # Atlas 200I SoC A1 核心板
    ["soc-core"]="host-arch=huawei-arm|huawei-x86 accelerator=huawei-Ascend310P servertype=soc"
)

# 可选标签（不强制要求）
declare -a OPTIONAL_LABELS=("nodeDEnable")

readonly REQUIRED_LABELS

readonly CONFIGMAP_PREFIX="mindx-dl-deviceinfo-"
#  ascend device plugin label
readonly DEVICE_PLUGIN_LABEL="name=ascend-device-plugin-ds"
# 在循环外部定义全局变量
declare -a resource_error_nodes=()

exit_code=0
problem_messages=()
warning_messages=()
info_messages=()

declare -a ascend_info_messages=()
declare -a cpu_info_messages=()
declare -a mem_info_messages=()
declare -a jq_info_messages=()

# 功能：根据产品类型获取对应的Ascend资源名称（用于后续资源检查）
# 参数：$1 - 产品类型字符串
get_ascend_resource_name() {
    local product_type=$1
    case "$product_type" in
        infer-card)
            echo "huawei.com/Ascend310"
            ;;
        infer-series|soc-core)
            echo "huawei.com/Ascend310P"
            ;;
        *)
            echo "huawei.com/Ascend910"
            ;;
    esac
}

# 功能：获取实际检测使用的Ascend资源名
#       优先使用自动探测结果（ASCEND_RESOURCE_NAME），否则根据产品类型推导
get_effective_ascend_resource_name() {
    if [[ -n "$ASCEND_RESOURCE_NAME" ]]; then
        echo "$ASCEND_RESOURCE_NAME"
    else
        echo "$(get_ascend_resource_name "$PRODUCT_TYPE")"
    fi
}

# 功能：从指定节点的资源中自动识别Ascend资源类型与卡数
#       规则：优先选 allocatable 为正整数的资源键（310/310P/910），并以该值作为期望卡数
#       若 jq 不可用，则直接设置默认值并返回成功
detect_ascend_from_node() {
    local node="$1"
    local node_json
    node_json=$(kubectl get node "$node" -o json 2>/dev/null)
    [[ -z "$node_json" ]] && return 1

    # 动态识别：枚举所有以 huawei.com/ 开头的 allocatable 资源键，找到第一个可用的正整数值作为期望卡数
    local res alloc
    while IFS= read -r res; do
        [[ -z "$res" ]] && continue
        alloc=$(jq -r ".status.allocatable.\"$res\"" <<< "$node_json" 2>/dev/null)
        if [[ "$alloc" =~ ^[0-9]+$ && "$alloc" -gt 0 ]]; then
            ASCEND_RESOURCE_NAME="$res"
            ASCEND_EXPECTED="$alloc"
            return 0
        fi
    done < <(jq -r '.status.allocatable | keys[]' <<< "$node_json" 2>/dev/null | grep -E '^huawei\.com/')

    return 1
}

# 功能：主节点检查流程，遍历所有Ready节点，执行各项检查
#       同时处理自动探测期望卡数的逻辑（若启用）
check_nodes() {
    # 获取所有Ready状态的node
    local nodes=$(kubectl get nodes -l workerselector=dls-worker-node -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}' | awk '$2 == "True" {print $1}')
    local notReadyNodes=$(kubectl get nodes -l workerselector=dls-worker-node -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}' | awk '$2 != "True" {print $1}')

    # 若用户未提供期望卡数：先基于第一个Ready节点自动定标（资源名 + 期望卡数）
    if [[ $ASCEND_EXPECTED_AUTO -eq 1 ]]; then
        if [[ $JQ_AVAILABLE -eq 0 ]]; then
            ASCEND_RESOURCE_NAME="huawei.com/Ascend910"
            ASCEND_EXPECTED="$DEFAULT_ASCEND_EXPECTED"
            info_messages+=("[自动识别] jq未安装，使用默认Ascend资源类型: $ASCEND_RESOURCE_NAME, 默认期望卡数: $ASCEND_EXPECTED")
        else
            local first_node
            first_node=$(echo "$nodes" | head -n 1)
            if [[ -z "$first_node" ]]; then
                problem_messages+=("[集群] 未找到Ready节点,无法自动识别Ascend资源与期望卡数")
                exit_code=1
                return
            fi
            if ! detect_ascend_from_node "$first_node"; then
                problem_messages+=("[$first_node] 无法自动识别Ascend资源类型(Ascend910/Ascend310P/Ascend310)或卡数,建议显式传入期望卡数")
                exit_code=1
                return
            fi
            info_messages+=("[自动识别] Ascend资源类型: $ASCEND_RESOURCE_NAME, 期望卡数: $ASCEND_EXPECTED (基于第一个Ready节点: $first_node)")
        fi
    fi

    for node in $notReadyNodes; do
        warning_messages+=("[$node] 运维告警：节点状态为NotReady")
    done

    for node in $nodes; do
        echo "检查节点: $node"

        # 检查不可调度状态
        check_unschedulable $node

        # 跳过不可调度节点的其他检查(kubectl cordon node)
        [[ $(kubectl get node $node -o jsonpath='{.spec.unschedulable}') == "true" ]] && continue

        # 执行完整检查流程,当产品类型不是 none 时才检查标签
        if [ "$PRODUCT_TYPE" != "none" ]; then
            check_node_labels $node $PRODUCT_TYPE
        fi
        check_network_status $node
        check_disk_pressure $node
        check_memory_pressure $node
        check_ascend_resource $node
        check_device_plugin $node
    done

    # 在所有节点检查完成后添加总结提示
    add_resource_error_summary
}

# 功能：检查节点是否被标记为不可调度（cordon）
check_unschedulable() {
    local node=$1
    local status=$(kubectl get node $node -o jsonpath='{.spec.unschedulable}')
    [[ "$status" == "true" ]] && {
        warning_messages+=("[$node] 运维告警：节点被标记为不可调度")
    }
}

# 功能：节点标签检查函数，包括公共标签、产品特定标签和可选标签
check_node_labels() {
    local node=$1
    local product_type=$2
    local -A node_labels

    # 可靠地获取节点标签
    while IFS= read -r label; do
        if [[ "$label" == *"="* ]]; then
            local key="$(echo "${label%%=*}" | xargs)"
            local value="${label#*=}"
            node_labels["$key"]="$value"
#            echo "获取标签： $key=$value"
        fi
    done < <(kubectl get node "$node" -o go-template='
        {{range $k, $v := .metadata.labels}}
            {{$k}}={{$v}}
        {{end}}
    ')

    # 检查公共标签
    check_label_group "common" "公共标签" "$node" node_labels

    # 检查产品特定标签
    if [[ -n "$product_type" && -n "${PRODUCT_LABEL_REQUIREMENTS[$product_type]}" ]]; then
        check_label_group "$product_type" "${PRODUCT_TYPES[$product_type]}" "$node" node_labels
    else
        problem_messages+=("[$node] 未配置或未知的产品类型: $product_type")
        exit_code=1
    fi

    # 检查可选标签
    for label in "${OPTIONAL_LABELS[@]}"; do
        if [[ -z "${node_labels[$label]}" ]]; then
            info_messages+=("[$node] 可选标签缺失: $label")
        fi
    done
}

# 功能：检查一组标签（如公共标签或产品标签）是否满足要求
check_label_group() {
    local group=$1
    local group_name=$2
    local node=$3
    local -n labels_ref=$4
    local label_errors=0

    # 获取该组的标签要求
    local requirements="${PRODUCT_LABEL_REQUIREMENTS[$group]}"

    # 检查每个标签要求
    while IFS= read -r req; do
        [[ -z "$req" ]] && continue

        local label_key="${req%%=*}"
        local expected_values="${req#*=}"
        local actual_value="${labels_ref[$label_key]}"

        # 检查标签是否存在
        if [[ -z "$actual_value" ]]; then
            problem_messages+=("[$node] [$group_name] 标签缺失: $label_key=$expected_values")
            label_errors=1
            continue
        fi

        # 检查标签值是否匹配
        local value_match=0
        IFS='|' read -ra exp_values <<< "$expected_values"
        for exp_value in "${exp_values[@]}"; do
            # 如果是正则表达式,使用模式匹配
            if [[ "$exp_value" == *"*"* ]]; then
                if [[ "$actual_value" =~ $exp_value ]]; then
                    value_match=1
                    break
                fi
            # 否则精确匹配
            elif [[ "$actual_value" == "$exp_value" ]]; then
                value_match=1
                break
            fi
        done

        if (( value_match == 0 )); then
            local pretty_expected="${expected_values//|/ 或 }"
            problem_messages+=("[$node] [$group_name] 标签值错误: $label_key=${actual_value} (期望: $pretty_expected)")
            label_errors=1
        fi
    done < <(echo "$requirements" | tr ' ' '\n')

    (( label_errors )) && exit_code=1
}

# 功能：检查节点网络状态（NetworkUnavailable条件是否为False）
check_network_status() {
    local node=$1
    local status=$(kubectl get node $node -o jsonpath='{.status.conditions[?(@.type=="NetworkUnavailable")].status}')
    [[ "$status" != "False" ]] && {
        problem_messages+=("[$node] 网络异常：NetworkUnavailable状态为'$status'(期望值: False)")
        exit_code=1
    }
}

# 功能：检查节点磁盘压力（DiskPressure条件是否为False）
check_disk_pressure() {
    local node=$1
    local status=$(kubectl get node $node -o jsonpath='{.status.conditions[?(@.type=="DiskPressure")].status}')
    [[ "$status" != "False" ]] && {
        problem_messages+=("[$node] 磁盘空间不足,请在对应节点执行df -h 查看磁盘使用情况并清理根目录,使根目录使用率降至85%以下,清理完成后等待一会儿自动恢复")
        exit_code=1
    }
}

# 功能：检查节点内存压力（MemoryPressure条件是否为False）
check_memory_pressure() {
    local node=$1
    local status=$(kubectl get node $node -o jsonpath='{.status.conditions[?(@.type=="MemoryPressure")].status}')
    [[ "$status" != "False" ]] && {
        problem_messages+=("[$node] 内存压力异常：MemoryPressure状态为'$status'(期望值: False)")
        exit_code=1
    }
}

# 功能：检查节点的Ascend资源（Capacity/Allocatable/Allocated）是否符合期望，并收集相关信息
#       若启用了内存/CPU检查，同时收集内存和CPU资源信息
check_ascend_resource() {
     local node=$1
     local ascend_resource
     ascend_resource="$(get_effective_ascend_resource_name)"
     # 创建转义版本(用于正则匹配场景)
     local escaped_resource="${ascend_resource//./\\.}"

     # 一次性获取所有节点信息并保存
     local node_json=$(kubectl get node $node -o json 2>/dev/null)
     local describe_output=$(kubectl describe node $node)

     local capacity=$(jq -r ".status.capacity.\"$ascend_resource\"" <<< "$node_json" 2>/dev/null)
     local allocatable=$(jq -r ".status.allocatable.\"$ascend_resource\"" <<< "$node_json" 2>/dev/null)

     # 如果jq不可用,回退到原始方法
     if [[ "$capacity" == "" || "$allocatable" == "" ]]; then
         capacity=$(kubectl get node $node -o jsonpath="{.status.capacity.$escaped_resource}" 2>/dev/null)
         allocatable=$(kubectl get node $node -o jsonpath="{.status.allocatable.$escaped_resource}" 2>/dev/null)
     fi

     local allocated=$(echo "$describe_output" | grep -A20 "Allocated resources" |
                       grep -w "$ascend_resource " |
                       awk '{print $2}' |
                       cut -d'(' -f1 |
                       tr -d ')')

     local formatted_info=$(printf "%-15s | Capacity(总卡数): %15s | Allocatable(可分配卡数): %15s | Allocated(已分配卡数): %15s" \
                           "[$node]" "${capacity:-N/A}" "${allocatable:-N/A}" "${allocated:-N/A}")
     ascend_info_messages+=("$formatted_info")

     local node_has_error=0
     local resource_warnings=()

     if [[ "${capacity:-0}" -ne "$ASCEND_EXPECTED" ]]; then
         resource_warnings+=("$(printf "%-35s" "[$node] Capacity异常:") 当前值 ${capacity:-N/A} (期望值 $ASCEND_EXPECTED)")
         node_has_error=1
         exit_code=1
     fi

     if [[ "${allocatable:-0}" -ne "$ASCEND_EXPECTED" ]]; then
         resource_warnings+=("$(printf "%-35s" "[$node] Allocatable异常:") 当前值 ${allocatable:-N/A} (期望值 $ASCEND_EXPECTED)")
         node_has_error=1
         exit_code=1
     fi

     if [[ "$CHECK_MEM_CPU" == "on" ]]; then
         # 从保存的JSON中提取内存和CPU信息
         local capacity_memory=$(jq -r '.status.capacity.memory' <<< "$node_json" 2>/dev/null)
         local allocatable_memory=$(jq -r '.status.allocatable.memory' <<< "$node_json" 2>/dev/null)
         local capacity_cpu=$(jq -r '.status.capacity.cpu' <<< "$node_json" 2>/dev/null)
         local allocatable_cpu=$(jq -r '.status.allocatable.cpu' <<< "$node_json" 2>/dev/null)

         # 如果jq不可用,回退到原始方法
         if [[ "$capacity_memory" == "" ]]; then
             capacity_memory=$(kubectl get node $node -o jsonpath="{.status.capacity.memory}" 2>/dev/null)
             allocatable_memory=$(kubectl get node $node -o jsonpath="{.status.allocatable.memory}" 2>/dev/null)
             capacity_cpu=$(kubectl get node $node -o jsonpath="{.status.capacity.cpu}" 2>/dev/null)
             allocatable_cpu=$(kubectl get node $node -o jsonpath="{.status.allocatable.cpu}" 2>/dev/null)
         fi

         # 从describe输出中提取已分配资源
         local allocated_memory=$(echo "$describe_output" | grep -A20 "Allocated resources" |
                               grep -w "memory " |
                               awk '{print $2$3}')
         local allocated_cpu=$(echo "$describe_output" | grep -A20 "Allocated resources" |
                               grep -w "cpu " |
                               awk '{print $2$3}')

         # 格式化内存信息
         local formatted_memory_info=$(printf "%-15s | Capacity(总内存): %15s | Allocatable(可分配内存): %15s | Allocated(已分配内存): %15s" \
                               "[$node]" "${capacity_memory:-N/A}" "${allocatable_memory:-N/A}" "${allocated_memory:-N/A}")
         mem_info_messages+=("$formatted_memory_info")

         # 格式化CPU信息
         local formatted_cpu_info=$(printf "%-15s | Capacity(总CPU): %16s | Allocatable(可分配CPU): %16s | Allocated(已分配CPU): %16s" \
                               "[$node]" "${capacity_cpu:-N/A}" "${allocatable_cpu:-N/A}" "${allocated_cpu:-N/A}")
         cpu_info_messages+=("$formatted_cpu_info")
     fi

     # 添加资源警告信息
     if (( node_has_error )); then
         problem_messages+=("${resource_warnings[@]}")
         resource_error_nodes+=("$node")
         check_configmap_npu $node
     fi
 }

# 功能：在所有节点检查完成后，汇总资源异常节点并给出排查建议
add_resource_error_summary() {
    if [ ${#resource_error_nodes[@]} -gt 0 ]; then
        warning_messages+=("${jq_info_messages[@]}")
        problem_messages+=("")
        problem_messages+=("注意: 以下节点出现Capacity/Allocatable异常: ${resource_error_nodes[*]}")
        problem_messages+=("      可能原因：1.存在卡故障(安装jq工具可自动解析故障信息);  2.节点上有进程占用Ascend设备资源")
        problem_messages+=("      排查建议：")

        # 为每个异常节点生成单独的查看命令
        for node in "${resource_error_nodes[@]}"; do
            problem_messages+=("        1. 查看节点 $node 的CM信息: kubectl describe cm -n kube-system ${CONFIGMAP_PREFIX}${node}")
        done

        problem_messages+=("        2. 登录节点执行 'npu-smi info' 查看占用进程")
    fi
}

# 功能：检查节点的设备信息ConfigMap，解析手动隔离的NPU和故障信息
check_configmap_npu() {
    local node=$1
    local cm_name="${CONFIGMAP_PREFIX}${node}"
    local ascend_resource
    ascend_resource="$(get_effective_ascend_resource_name)"
    local fault_resource="${ascend_resource}-Fault"

    # 检查ConfigMap是否存在
    if ! kubectl get cm -n kube-system "$cm_name" &>/dev/null; then
        warning_messages+=("[$node] 配置异常：未找到设备信息ConfigMap ${cm_name}")
        return 1
    fi

    local npu_flag=$(kubectl get cm -n kube-system "$cm_name" \
        -o jsonpath='{.data.ManuallySeparateNPU}' 2>/dev/null)

    [[ -n "$npu_flag" ]] && {
        warning_messages+=("[$node] 配置告警：检测到被手动隔离的NPU卡（隔离列表：${npu_flag}）")
        warning_messages+=("      恢复步骤：")
        warning_messages+=("        1. 确认故障已解决")
        warning_messages+=("        2. 执行命令: kubectl edit cm -n kube-system ${cm_name}")
        warning_messages+=("        3. 删除ManuallySeparateNPU所在行")
        warning_messages+=("        4. 保存退出")
    }

    local device_info_cfg=$(kubectl get cm -n kube-system "$cm_name" \
        -o jsonpath='{.data.DeviceInfoCfg}' 2>/dev/null)

    [[ -z "$device_info_cfg" ]] && {
        warning_messages+=("[$node] 配置异常：DeviceInfoCfg字段为空")
        return 0
    }

    local fault_info=$(echo "$device_info_cfg" |
        jq -r ".DeviceInfo.DeviceList.\"$fault_resource\"" 2>/dev/null)

    # 使用全局变量检查jq可用性
    if [[ $JQ_AVAILABLE -eq 0 ]]; then
        return 0
    fi

    [[ -z "$fault_info" || "$fault_info" == "null" ]] && return 0

    # 解析并格式化故障信息
    warning_messages+=("[$node] 故障信息报告：")

    # 提取故障数量
    local fault_count=$(echo "$fault_info" | jq 'length')
    warning_messages+=("  - 总故障数量: $fault_count")

    # 解析每个故障条目
    for i in $(seq 0 $(($fault_count - 1))); do
        local fault_entry=$(echo "$fault_info" | jq -r ".[$i]")

        local npu_name=$(echo "$fault_entry" | jq -r '.npu_name')
        local fault_type=$(echo "$fault_entry" | jq -r '.fault_type')
        local fault_code=$(echo "$fault_entry" | jq -r '.fault_code')
        local fault_level=$(echo "$fault_entry" | jq -r '.fault_level')
        local fault_handling=$(echo "$fault_entry" | jq -r '.fault_handling')

        # 提取故障时间信息
        local time_info=$(echo "$fault_entry" | jq -r '.fault_time_and_level_map | to_entries[] |
            "故障代码: \(.key), 故障时间: \((.value.fault_time / 1000) | strftime("%Y-%m-%d %H:%M:%S")), 级别: \(.value.fault_level)"' |
            sed 's/^/            /')

        warning_messages+=("  - NPU卡: $npu_name")
        warning_messages+=("    - 故障类型: $fault_type")
        warning_messages+=("    - 故障代码: $fault_code")
        warning_messages+=("    - 故障级别: $fault_level")
        warning_messages+=("    - 处理状态: $fault_handling")
        warning_messages+=("    - 详细时间记录:")
        warning_messages+=("$time_info")
    done
}

# 功能：检查 mindx-dl 命名空间下的 cluster-info-node-cm ConfigMap，解析节点状态和故障设备
check_cluster_info_node-cm() {
    local cm_name="cluster-info-node-cm"
    local namespace="mindx-dl"
    local cm_data

    # 检查 ConfigMap 是否存在
    if ! kubectl get cm -n "$namespace" "$cm_name" &>/dev/null; then
        return
    fi

    cm_data=$(kubectl get cm -n "$namespace" "$cm_name" -o jsonpath="{.data.$cm_name}" 2>/dev/null)
    if [[ -z "$cm_data" ]]; then
        return
    fi

    # 检查 jq 可用性
    if [[ $JQ_AVAILABLE -eq 0 ]]; then
        warning_messages+=("[$cm_name] 未安装 jq，无法解析节点状态")
        return
    fi

    local has_fault=0
    # 提取节点信息
    while read -r node_key; do
        # 使用引号包围键名来避免jq解析问题
        local node_info=$(echo "$cm_data" | jq -r ".\"$node_key\"")
        local node_name=${node_key#mindx-dl-nodeinfo-}
        local node_status=$(echo "$node_info" | jq -r '.NodeStatus')

        # 检查FaultDevList是否为null或空数组
        local fault_dev_list=$(echo "$node_info" | jq -r '.FaultDevList')
        local has_fault_devices=0

        # 判断是否有故障设备
        if [[ "$fault_dev_list" != "null" && "$fault_dev_list" != "[]" ]]; then
            has_fault_devices=1
        fi

        # 只显示非健康节点或有故障设备的节点
        if [[ "$node_status" != "Healthy" || $has_fault_devices -eq 1 ]]; then
            has_fault=1
            local msg="[$node_name] 节点状态: $node_status"

            # 添加故障设备信息
            if [[ $has_fault_devices -eq 1 ]]; then
                msg+=", 故障设备:"
                # 使用索引循环来避免JSON解析问题
                local fault_count=$(echo "$node_info" | jq '.FaultDevList | length')
                for i in $(seq 0 $((fault_count - 1))); do
                    local device=$(echo "$node_info" | jq -r ".FaultDevList[$i]")
                    if [[ -n "$device" && "$device" != "null" ]]; then
                        local dev_type=$(echo "$device" | jq -r '.DeviceType')
                        local dev_id=$(echo "$device" | jq -r '.DeviceId')
                        local fault_code=$(echo "$device" | jq -r '.FaultCode | join(", ")')
                        local fault_level=$(echo "$device" | jq -r '.FaultLevel')
                        msg+=$'\n  - 类型: '"$dev_type"', ID: '"$dev_id"', 故障码: ['"$fault_code"'], 等级: '"$fault_level"
                    fi
                done
            fi

            # 根据状态分类
            if [[ "$node_status" == "UnHealthy" ]]; then
                problem_messages+=("$msg")
            else
                warning_messages+=("$msg")
            fi
        fi
    done < <(echo "$cm_data" | jq -r 'keys[]')

    [[ $has_fault -eq 0 ]] && info_messages+=("cluster-info-node-cm: 所有节点状态正常")
}

# 功能：检查 mindx-dl 命名空间下的 cluster-info-switch-0 ConfigMap，解析交换机状态
check_cluster_info_switch() {
    local cm_name="cluster-info-switch-0"
    local namespace="mindx-dl"
    local cm_data

    # 检查 ConfigMap 是否存在
    if ! kubectl get cm -n "$namespace" "$cm_name" &>/dev/null; then
        return
    fi

    cm_data=$(kubectl get cm -n "$namespace" "$cm_name" -o jsonpath="{.data.$cm_name}" 2>/dev/null)
    if [[ -z "$cm_data" ]]; then
        return
    fi

    # 检查 jq 可用性
    if [[ $JQ_AVAILABLE -eq 0 ]]; then
        warning_messages+=("[$cm_name] 未安装 jq，无法解析交换机状态")
        return
    fi

    local has_fault=0
    local switch_keys
    switch_keys=$(jq -r 'keys[]' <<<"$cm_data" 2>/dev/null)

    while IFS= read -r switch_key; do
        [[ -z "$switch_key" ]] && continue

        local switch_info
        switch_info=$(jq -r ".[\"$switch_key\"]" <<<"$cm_data" 2>/dev/null)

        local node_status=$(jq -r '.NodeStatus' <<<"$switch_info")
        local fault_level=$(jq -r '.FaultLevel' <<<"$switch_info")
        local fault_code_count=$(jq -r '.FaultCode | length' <<<"$switch_info")
        local update_time=$(jq -r '.UpdateTime' <<<"$switch_info")
        local cm_name_field=$(jq -r '.CmName' <<<"$switch_info")

        # 格式化时间（如果 UpdateTime 是秒级时间戳）
        local time_str="未知"
        if [[ "$update_time" =~ ^[0-9]+$ ]]; then
            time_str=$(date -d @"$update_time" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$update_time")
        fi

        # 判断是否异常：NodeStatus 不是 Healthy 或 FaultCode 非空
        if [[ "$node_status" != "Healthy" ]] || [[ "$fault_code_count" -gt 0 ]]; then
            has_fault=1
            local msg="[$switch_key] 交换机状态异常"
            msg+=" | NodeStatus: $node_status"
            msg+=" | 故障数量: $fault_code_count"
            msg+=" | 故障等级: ${fault_level:-无}"
            msg+=" | 更新时间: $time_str"

            if [[ "$node_status" == "UnHealthy" ]]; then
                problem_messages+=("$msg")
            else
                warning_messages+=("$msg")
            fi

            # 可选：输出每个故障码的详细信息
            if [[ $fault_code_count -gt 0 ]]; then
                local i
                for i in $(seq 0 $((fault_code_count - 1))); do
                    local fault_entry
                    fault_entry=$(jq -r ".FaultCode[$i]" <<<"$switch_info")
                    # 尝试解析故障码内部 JSON（如果 fault_entry 是字符串 JSON）
                    if [[ "$fault_entry" =~ ^\{.*\}$ ]]; then
                        local assembled_fault=$(jq -r '.AssembledFaultCode' <<<"$fault_entry" 2>/dev/null)
                        local severity=$(jq -r '.Severity' <<<"$fault_entry" 2>/dev/null)
                        local alarm_time=$(jq -r '.AlarmRaisedTime' <<<"$fault_entry" 2>/dev/null)
                        # 转换时间戳（毫秒转秒）
                        if [[ "$alarm_time" =~ ^[0-9]+$ ]]; then
                            alarm_time=$(date -d @"$(($alarm_time/1000))" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$alarm_time")
                        fi
                        warning_messages+=("    - 故障码: $assembled_fault | 严重级: $severity | 告警时间: $alarm_time")
                    else
                        warning_messages+=("    - 故障码原始数据: $fault_entry")
                    fi
                done
            fi
        fi
    done <<< "$switch_keys"

    if [[ $has_fault -eq 0 ]]; then
        info_messages+=("[$cm_name] 所有交换机状态正常")
    fi
}

# 功能：检查系统是否安装了 jq 工具，并设置全局变量 JQ_AVAILABLE
check_jq_installed() {
    if ! command -v jq &> /dev/null; then
        jq_info_messages+=("系统警告：jq工具未安装,部分功能受限")
        jq_info_messages+=("  安装方法:")
        jq_info_messages+=("    Ubuntu/Debian: sudo apt-get install jq")
        jq_info_messages+=("    CentOS/RHEL: sudo yum install jq")
        jq_info_messages+=("  离线安装:")
        jq_info_messages+=("    使用压缩包中的jq-*进行安装： chmod +x jq-linux-`arch`;cp jq-linux-`arch` /usr/local/bin/jq")
        JQ_AVAILABLE=0
    else
        JQ_AVAILABLE=1
    fi
}

# 功能：检查节点上的 device-plugin Pod 是否正常运行，并获取日志片段
check_device_plugin() {
    local node=$1
    # 单次调用获取所有必要信息
    local pod_info=$(kubectl get pod -n kube-system \
        --field-selector spec.nodeName=$node \
        -l "${DEVICE_PLUGIN_LABEL}" \
        -o jsonpath='{range .items[0]}{.status.phase}{","}{.metadata.deletionTimestamp}{","}{.metadata.name}{end}' 2>/dev/null)

    # 拆分获取的信息
    IFS=',' read -r plugin_status deletion_timestamp plugin_pod <<< "$pod_info"

    # 检测异常条件：非运行状态 或 存在删除时间戳
    if [[ -z "$plugin_pod" ]]; then
        problem_messages+=("[$node] device-plugin 异常：未找到运行实例")
        exit_code=1
        return
    fi

    if [[ "$plugin_status" != "Running" || -n "$deletion_timestamp" ]]; then
        problem_messages+=("[$node] device-plugin 未正常运行 (状态: ${plugin_status:-Unknown}${deletion_timestamp:+, Terminating})")
        exit_code=1

        # 获取日志（兼容 Terminating 状态）
        local recent_logs
        if kubectl get pod -n kube-system "$plugin_pod" &>/dev/null; then
            recent_logs=$(kubectl logs -n kube-system "$plugin_pod" --tail=10 2>/dev/null | sed 's/^/    /')
        else
            recent_logs="    [警告] Pod 已终止,无法获取日志"
        fi

        problem_messages+=(
            "[$node] device-plugin 日志片段(查看完整日志命令：kubectl logs -f -n kube-system ${plugin_pod}):"
            "$recent_logs"
        )
    fi
}

# 功能：主函数，依次执行各项检查并输出结果
main() {
    echo "=== 集群健康检查启动 ==="
    check_jq_installed
    check_nodes
    check_cluster_info_node-cm
    check_cluster_info_switch
    echo -e "\n=== 资源状态 ==="
    if [ ${#ascend_info_messages[@]} -gt 0 ]; then
        echo "Ascend资源状态($(get_effective_ascend_resource_name)):"
        printf '  %s\n' "${ascend_info_messages[@]}"
        echo
    fi
    if [[ "$CHECK_MEM_CPU" == "on" && ${#cpu_info_messages[@]} -gt 0 ]]; then
        echo "CPU资源状态:"
        printf '  %s\n' "${cpu_info_messages[@]}"
        echo
    fi
    if [[ "$CHECK_MEM_CPU" == "on" && ${#mem_info_messages[@]} -gt 0 ]]; then
        echo "内存资源状态:"
        printf '  %s\n' "${mem_info_messages[@]}"
        echo
    fi
    if [ ${#info_messages[@]} -gt 0 ]; then
        echo "其他信息:"
        printf '  %s\n' "${info_messages[@]}"
        echo
    fi
    [[ ${#warning_messages[@]} -gt 0 ]] && {
        echo -e "\n=== 运维注意 ==="
        printf '  %s\n' "${warning_messages[@]}"
    }
    if [[ $exit_code -eq 0 ]]; then
        echo -e "\n=== 检查结果 ===\n环境状态正常"
    else
        echo -e "\n=== 故障详情 ==="
        printf '  %s\n' "${problem_messages[@]}"
    fi

    exit $exit_code
}

main