import pyvisa
import time
# KIKUSUI PMX18-5A 電源モジュールの制御クラス
# このクラスは、KIKUSUI PMX18-5A 電源モジュールを制御するための基本的な機能を提供します。   

class Application:
    def __init__(self):
        self.inst = None
        self.rm = pyvisa.ResourceManager()
        self.foundResources = self._list_resources()
        self.res_text = ''

    def _list_resources(self):
        try:
            found = self.rm.list_resources("?*INSTR")
            if not found:
                raise Exception
            return found
        except Exception:
            self.res_text = '接続先対象が見つかりませんでした'
            return ('None',)

    def Open(self, addr):
        try:
            self.inst = self.rm.open_resource(addr)
            if self.inst.interface_type == 4:  # RS232C(ASRL)
                self.inst.baud_rate = 19200
                self.inst.data_bits = 8
                self.inst.parity = pyvisa.constants.Parity.none
                self.inst.stop_bits = pyvisa.constants.StopBits.two
                self.inst.flow_control = pyvisa.constants.ControlFlow.xon_xoff
                # パラメータ変数
                #   parity:  none, odd, even, mark, space
                #   stopbit: one, one_and_a_half, two
                #   flowcontrol: none, xon_xoff, rts_cts, dtr_dsr
            elif self.inst.interface_type == 6:  # TCPIP
                pass
            elif self.inst.interface_type == 7:  # USB
                pass
            elif self.inst.interface_type == 1:  # GPIB
                self.inst.read_termination = '\r'
            self.inst.read_termination = '\n'
            self.inst.write_termination = '\n'
            str_comment = 'KIKUSUI VISAセッションオープンに成功しました' + '\n'
            str_comment += self.inst.query("*IDN?")+  '\n' # IDNクエリ
            return True, str_comment
        except Exception:
            return False, 'KIKUSUI VISAセッションオープンに失敗しました'

    def Write_Command(self, command):
        # コマンドリスト
        cmb_CommandString = ["SYST:REMOTE", "SYST:LOCAL", "*CLS", "OUTP ON", "OUTP OFF", "VOLT 10", "VOLT 1", "CURR 1", "CURR 0.1"]
        if self.inst:
            self.inst.write(command)

    def Query(self, command):
        # クエリコマンドリスト
        cmb_QueryString = ["*IDN?", "*STB?", "SYST:ERR?", "OUTP?", "VOLT?", "CURR?", "MEAS:VOLT?", "MEAS:CURR?"]
        if not self.inst:
            return '機器がオープンされていません'
        try:
            return self.inst.query(command)
        except pyvisa.Error as ex:
            return f'クエリメッセージ受信に失敗しました: {ex}'

    def Serial_Poll(self):
        if self.inst:
            return self.inst.read_stb()
        return None

    def Close(self):
        if self.inst:
            self.inst.close()
            self.inst = None

    def get_resources(self):
        return self.foundResources

    def get_last_error(self):
        return self.res_text
    
    def Get_Status(self):
        cmb_QueryString = self.Query('STAT:OPER?')
        decimal_num = int(cmb_QueryString)
        binary_str = f"{decimal_num:0=#18b}" # 16ビットの2進数表現に変換 出力例　ステータスビット: 0b0000001100000000
        cc_flag_str = binary_str[7]
        output_flag_str = binary_str[8]
        cv_flag_str = binary_str[9]
        return binary_str,cc_flag_str, cv_flag_str, output_flag_str


# --- 使い方サンプル ---
if __name__ == "__main__":
    ps = Application()
    print("利用可能なリソース:", ps.get_resources())
    addr = ps.get_resources()[0]
    ok, msg = ps.Open(addr)
    print(msg)
    if ok:
        # print("VOLT:PROT:STAT?", ps.Query("VOLT:PROT:STAT?"))

        binary_str,cc_flag_str, cv_flag_str, output_flag_str = ps.Get_Status()
        print("ステータスビット:", binary_str)
        print("CCフラグ:", cc_flag_str)
        print("CVフラグ:", cv_flag_str)
        print("出力フラグ:", output_flag_str)

        print("IDN:", ps.Query("*IDN?"))
        ps.Write_Command("SYST:REMOTE")
        ps.Write_Command("OUTP ON")
        ps.Write_Command("VOLT 4.0")
        print("MEAS:VOLT?(V)", ps.Query("MEAS:VOLT?"))
        print("MEAS:CURR?(A)", ps.Query("MEAS:CURR?"))

        binary_str,cc_flag_str, cv_flag_str, output_flag_str = ps.Get_Status()
        print("ステータスビット:", binary_str)
        print("CCフラグ:", cc_flag_str)
        print("CVフラグ:", cv_flag_str)
        print("出力フラグ:", output_flag_str)

        time.sleep(10.0)  # 10秒待機 
        binary_str,cc_flag_str, cv_flag_str, output_flag_str = ps.Get_Status()
        print("ステータスビット:", binary_str)
        print("CCフラグ:", cc_flag_str)
        print("CVフラグ:", cv_flag_str)
        print("出力フラグ:", output_flag_str)

        ps.Write_Command("VOLT 0.0")
        print("MEAS:VOLT?(V)", ps.Query("MEAS:VOLT?"))
        print("MEAS:CURR?(A)", ps.Query("MEAS:CURR?"))

        time.sleep(2.0)  # 2秒待機
        ps.Write_Command("OUTP OFF")
        ps.Write_Command("SYST:LOCAL")
        ps.Close()