package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;
import java.lang.reflect.Field;

public class BankAccount_withdraw_Dbl_Test_Normal_6 {


    @Test
    public void testWithdrawValidAmountReducesBalance() throws Exception {
        BankAccount account = new BankAccount("Alice", 100.0);

        account.withdraw(1.0);

        Field balanceField = BankAccount.class.getDeclaredField("balance");
        balanceField.setAccessible(true);
        double balance = (Double) balanceField.get(account);

        Assertions.assertEquals(99.0, balance, 0.0001);
    }

}